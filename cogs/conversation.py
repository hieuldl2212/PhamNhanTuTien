"""Cog xử lý hội thoại với AI"""
import discord
from discord.ext import commands
from groq import AsyncGroq
from config import GROQ_API_KEY
import google.generativeai as genai
from google import genai
from config import GEMINI_API_KEY
from database import get_user_state, update_user_state
from utils.personalities import PERSONALITIES, MOODS, get_sect_info, get_user_role_info

class ConversationHandler(commands.Cog):
    """Xử lý hội thoại với Groq API"""
    
    def __init__(self, bot):
        self.bot = bot
        # Khởi tạo AsyncClient của Groq (không gây nghẽn event loop của discord.py)
        self.client = AsyncGroq(api_key=GROQ_API_KEY)
        self.model_name = 'llama-3.1-8b-instant'
        
    @commands.Cog.listener()
    async def on_message(self, message):
        """Lắng nghe và phản hồi tin nhắn"""
        if message.author == self.bot.user:
            return
        
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return
        
        if not (self.bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel)):
            return
        
        print(f"📩 Nhận tin nhắn từ {message.author}: {message.content}")
        
        user_id = message.author.id
        
        thinking_msg = await message.reply("💭 Đang suy nghĩ...")
        
        try:
            state = get_user_state(user_id)
            sect_info = get_sect_info(state['sect'])
            role_info = get_user_role_info(state['user_role'])
            personality_data = PERSONALITIES[state['personality']]
            
            # Tạo system prompt với role
            system_prompt = f"""
{personality_data['base']}

Xuất thân: Bạn thuộc {sect_info['name']} - {sect_info['description']}
Đặc trưng tông môn: {sect_info['specialty']}

Vai trò: Người đối thoại là {role_info['name']} của bạn ({role_info['description']})
Cách xưng hô:
- Bạn tự xưng: {role_info['address_to_bot']}
- Bạn gọi người đối thoại: {role_info['bot_address_to_user']}

Phong cách nói: {personality_data['speech_style']}

Tâm trạng hiện tại: {MOODS[state['mood']]}

Quan trọng:
- Luôn gọi người đối thoại theo đúng vai trò: "{role_info['bot_address_to_user']}"
- Tự xưng là: "{role_info['address_to_bot']}"
- Trả lời bằng tiếng Việt, phong cách tu tiên/võ hiệp
- Có thể nhắc đến tông môn, võ công, pháp bảo khi phù hợp
- Thể hiện rõ tính cách {state['personality']} trong cách nói
- Điều chỉnh thái độ theo vai trò (tôn trọng sư phụ, chăm sóc sư đệ, ngang hàng với đạo hữu)
- Trả lời tối đa 150 từ.
- Không lặp lại cùng một ý nhiều lần.
- Không lặp lại cùng một hành động.
- Không lặp lại cùng một câu.
- Không nhắc lại tên người đối thoại quá nhiều.
- Không tự kể chuyện dài dòng.
- Trả lời tự nhiên như đang chat.
- Mỗi phản hồi chỉ nên có 1-2 đoạn.
-Không được tự bịa lịch sử tông môn.
-Không được tạo trưởng lão mới.
-Không được tạo nhân vật mới.
-Chỉ sử dụng thông tin đã được cung cấp.
-Nếu không biết thì nói "đệ tử không rõ".
-Không viết theo dạng tiểu thuyết.
-Không mô tả hành động sau mỗi câu.
-Chỉ mô tả hành động khi thật sự cần.
-Ưu tiên hội thoại.
-Giống như đang trò chuyện trên Discord.
"""
            
            prompt = f"{system_prompt}\n\n"
            
            for msg in state['history'][-5:]:
                role = role_info['bot_address_to_user'].title() if msg['role'] == 'user' else role_info['address_to_bot'].title()
                prompt += f"{role}: {msg['content']}\n"
            
            user_content = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
            prompt += f"{role_info['bot_address_to_user'].title()}: {user_content}\n{role_info['address_to_bot'].title()}:"
            
            print(f"🤖 Đang gọi Groq API...")
            
            # Thay thế lệnh gọi API Gemini bằng Groq Chat Completion chuẩn OpenAI
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}]
            )
            reply_text = response.choices[0].message.content
            
            print(f"✅ Nhận được phản hồi: {reply_text[:50]}...")
            
            state['history'].append({"role": "user", "content": user_content})
            state['history'].append({"role": "assistant", "content": reply_text})
            update_user_state(user_id, history=state['history'])
            
            await thinking_msg.delete()
            
            color_map = {
                'tsundere': 0xFF69B4,
                'kuudere': 0x87CEEB,
                'dandere': 0xDDA0DD,
                'deredere': 0xFFD700,
                'himedere': 0xFF1493,
                'yandere': 0xFF0066,
                'oneesan': 0xFFB6C1,
                'genki': 0xFFD700,
                'megane': 0x4169E1,
                'ojousama': 0xDA70D6,
                'kawaii': 0xFFB6C1,
                'baka': 0xFFA500
            }
            
            embed = discord.Embed(
                title="Trả lời",
                description=reply_text[:4096],
                color=color_map.get(state['personality'], 0x00ff00)
            )
            
            embed.set_footer(
                text=f"{sect_info['name']} • {state['personality'].title()} • {state['mood']} • {role_info['name']}"
            )
            
            if len(reply_text) > 4096:
                await message.reply(embed=embed)
                
                remaining = reply_text[4096:]
                chunks = [remaining[i:i+4096] for i in range(0, len(remaining), 4096)]
                
                for i, chunk in enumerate(chunks):
                    continuation_embed = discord.Embed(
                        title=f"Trả lời (tiếp theo {i+2})",
                        description=chunk,
                        color=color_map.get(state['personality'], 0x00ff00)
                    )
                    await message.channel.send(embed=continuation_embed)
            else:
                await message.reply(embed=embed)
                
        except Exception as e:
            print(f"❌ Lỗi: {type(e).__name__}: {str(e)}")
            
            try:
                await thinking_msg.delete()
            except:
                pass
            
            error_embed = discord.Embed(
                title="❌ Lỗi",
                description=f"Xin lỗi, gặp chút vấn đề:\n``````",
                color=0xFF0000
            )
            await message.reply(embed=error_embed)

async def setup(bot):
    await bot.add_cog(ConversationHandler(bot))
