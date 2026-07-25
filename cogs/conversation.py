"""Cog xử lý hội thoại với AI"""
import discord
from discord.ext import commands
import google.generativeai as genai
from google import genai
from config import GEMINI_API_KEY
from database import get_user_state, update_user_state
from utils.personalities import PERSONALITIES, MOODS, get_sect_info, get_user_role_info

class ConversationHandler(commands.Cog):
    """Xử lý hội thoại với Gemini API"""
    
    # def __init__(self, bot):
    #     self.bot = bot
    #     genai.configure(api_key=GEMINI_API_KEY)
    #     self.model = genai.GenerativeModel('gemini-2.5-flash')
    def __init__(self, bot):
        self.bot = bot
        # Khởi tạo Client bằng SDK google-genai mới
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model_name = 'gemini-2.0-flash'
        
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
"""
            
            prompt = f"{system_prompt}\n\n"
            
            for msg in state['history'][-5:]:
                role = role_info['bot_address_to_user'].title() if msg['role'] == 'user' else role_info['address_to_bot'].title()
                prompt += f"{role}: {msg['content']}\n"
            
            user_content = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
            prompt += f"{role_info['bot_address_to_user'].title()}: {user_content}\n{role_info['address_to_bot'].title()}:"
            
            print(f"🤖 Đang gọi Gemini API...")
            
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)
            reply_text = response.text
            
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
