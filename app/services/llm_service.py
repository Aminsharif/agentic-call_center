from typing import List, Dict
import os
from dotenv import load_dotenv
import groq

# Load environment variables
load_dotenv()

class LLMService:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        self.client = groq.Groq(api_key=self.api_key)
        
        self.system_prompt = """You are an AI customer service agent. Your goal is to help customers with their inquiries in a professional, friendly, and efficient manner. You should:
1. Be polite and empathetic
2. Ask clarifying questions when needed
3. Provide accurate and helpful information
4. Keep responses concise but informative
5. Use a natural, conversational tone"""

    def get_response(self, message: str) -> str:
        """Get a response from the LLM"""
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": message}
                ],
                model="mixtral-8x7b-32768",
                temperature=0.7,
                max_tokens=1000,
                top_p=1,
                stream=False
            )
            
            return chat_completion.choices[0].message.content
            
        except Exception as e:
            error_msg = str(e)
            print(f"Error in LLM response: {error_msg}")  # Add logging
            raise Exception(f"Error getting LLM response: {error_msg}")

    def format_conversation_history(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Format the conversation history for the LLM.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            List[Dict[str, str]]: Formatted conversation history
        """
        formatted_messages = [{"role": "system", "content": self.system_prompt}]
        formatted_messages.extend(messages)
        return formatted_messages 