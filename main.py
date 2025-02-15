from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from openai import OpenAI
import requests
import json
import os
import re

@register("prompt", "yudengghost", "AI提示词助手插件", "1.0.0", "repo url")
class MyPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config
        self.model_type = self.config.get("model_type", "deepseek")
        
        if self.model_type == "deepseek":
            deepseek_config = self.config.get("deepseek_config", {})
            self.client = OpenAI(
                api_key=deepseek_config.get("api_key"),
                base_url=deepseek_config.get("base_url", "https://api.deepinfra.com/v1/openai")
            )
        else:  # gemini
            gemini_config = self.config.get("gemini_config", {})
            self.api_key = gemini_config.get("api_key")
            self.model = gemini_config.get("model", "gemini-2.0-flash")
            self.url = f"https://dynamic-halva-76bb38.netlify.app/v1/models/{self.model}:generateContent"
            self.params = {
                "key": self.api_key
            }
            self.headers = {
                "Content-Type": "application/json"
            }
    
    @filter.command("提示词")
    async def prompt(self, event: AstrMessageEvent):
        """使用AI模型生成回复的提示词命令"""
        # 获取用户消息
        user_message = event.message_str
        
        # 发送等待提示
        yield event.plain_result("正在思考中，请稍候...")
        
        try:
            if self.model_type == "deepseek":
                # DeepSeek模型请求
                deepseek_config = self.config.get("deepseek_config", {})
                messages = [{"role": "system", "content": self.config.get("system_message")}] if self.config.get("system_message") else []
                messages.append({"role": "user", "content": user_message})
                
                chat_completion = self.client.chat.completions.create(
                    model=deepseek_config.get("model", "deepseek-ai/DeepSeek-R1"),
                    messages=messages,
                    temperature=self.config.get("model_settings", {}).get("temperature", 0.7),
                    max_tokens=self.config.get("model_settings", {}).get("max_tokens", 4096)
                )
                 # 获取响应并处理
                response_text = chat_completion.choices[0].message.content
                # 删除<think>到</think>之间的所有内容（包括标签本身）
                response_text = re.sub(r'<think>[\s\S]*?</think>', '', response_text)
                
            else:  # gemini
                # Gemini模型请求
                # 构建消息内容，将system message作为用户消息的前缀
                full_message = user_message
                if self.config.get("system_message"):
                    full_message = f"{self.config.get('system_message')}\n\n用户消息：{user_message}"
                
                contents = [{
                    "role": "user",
                    "parts": [{"text": full_message}]
                }]
                
                data = {
                    "contents": contents,
                    "generation_config": {
                        "temperature": self.config.get("model_settings", {}).get("temperature", 0.7),
                        "maxOutputTokens": self.config.get("model_settings", {}).get("max_tokens", 4096)
                    }
                }
                
                # 发送请求
                response = requests.post(self.url, params=self.params, headers=self.headers, json=data)
                
                # 记录响应内容用于调试
                logger.info(f"Gemini API Response: {response.text}")
                
                if response.status_code != 200:
                    raise Exception(f"API请求失败，状态码: {response.status_code}, 响应: {response.text}")
                
                json_data = response.json()
                
                # 检查响应格式
                if "error" in json_data:
                    raise Exception(f"API返回错误: {json_data['error']}")
                
                # 获取响应文本
                try:
                    response_text = json_data.get("candidates", [])[0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError) as e:
                    logger.error(f"解析响应失败: {json_data}")
                    raise Exception(f"无法解析API响应: {str(e)}")
            
            # 返回响应
            yield event.plain_result(response_text.strip())
            
        except Exception as e:
            logger.error(f"处理提示词命令时出错: {str(e)}")
            yield event.plain_result(f"抱歉，处理请求时出现错误: {str(e)}")
            # 打印详细错误信息到日志
            logger.error(f"详细错误信息: {e}", exc_info=True)