import discord
from discord.ext import commands
import json
import os
import sys

# ================== TOKEN ==================
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ ERRO: DISCORD_TOKEN não definido")
    sys.exit(1)

# ================== DATABASE ==================
DB_FILE = "database.json"

def load_db():
    if not os.path.exists(DB_FILE):
        return {
            "config": {
                "pix": "Não configurado",
                "cargo_owner": None,
                "cat_suporte": None
            }
        }
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

db = load_db()

# ================== PACOTES ==================
PACOTES_SALAS = {
    "50": {"label": "10 Salas 💎", "preco": "R$ 3,00", "mensagem": "Crie Sala Automaticamente!"},
    "100": {"label": "30 Salas 💎", "preco": "R$ 6,00", "mensagem": "Crie Sala Automaticamente!"},
    "300": {"label": "50 Salas 💎", "preco": "R$ 10,00", "mensagem": "Crie Sala Automaticamente!"},
    "500": {"label": "100 Salas 💎", "preco": "R$ 18,00", "mensagem": "Crie Sala Automaticamente!"},
    "1000": {"label": "300 Salas 💎", "preco": "R$ 60,00", "mensagem": "Crie Sala Automaticamente!"}
}

# ================== VIEW ADMIN ==================
class AdminActions(discord.ui.View):
    def __init__(self, cliente_id, produto_nome):
        super().__init__(timeout=None)
        self.cliente_id = cliente_id
        self.produto = produto_nome

    @discord.ui.button(label="Aprovar Pagamento", style=discord.ButtonStyle.success, emoji="✅")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if db["config"]["cargo_owner"] not in [r.id for r in interaction.user.roles]:
            return await interaction.response.send_message("❌ Apenas o dono pode aprovar.", ephemeral=True)

        membro = interaction.guild.get_member(self.cliente_id)
        if membro:
            await interaction.channel.send(
                f"✅ **Pagamento Aprovado!**\n{membro.mention}, **aguarde estamos preparando seu produto!**"
            )
            await interaction.response.send_message("Confirmado!", ephemeral=True)

    @discord.ui.button(label="Fechar Carrinho", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if db["config"]["cargo_owner"] not in [r.id for r in interaction.user.roles]:
            return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
        await interaction.channel.delete()

# ================== VIEW PRODUUP ==================
class ProduUpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        options = [
            discord.SelectOption(
                label=f"{v['label']} - {v['preco']}",
                description=v["mensagem"],
                value=k
            ) for k, v in PACOTES_SALAS.items()
        ]

        select = discord.ui.Select(
            placeholder="📦 Escolha o seu pacote de salas",
            options=options
        )
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        data = PACOTES_SALAS[interaction.data["values"][0]]

        embed = discord.Embed(
            title="📊 Pacote Selecionado",
            description=(
                f"Pacote: **{data['label']}**\n"
                f"Preço: **{data['preco']}**\n\n"
                "Clique no botão abaixo para abrir o carrinho."
            ),
            color=discord.Color.orange()
        )

        embed.set_image(
            url="https://cdn.discordapp.com/attachments/1447763890225287269/1455736408898797729/ChatGPT_Image_30_de_dez._de_2025_22_36_10.png"
        )

        button = discord.ui.Button(label="Abrir Carrinho", style=discord.ButtonStyle.green, emoji="🛒")

        async def abrir(inter):
            cfg = db["config"]
            guild = inter.guild
            categoria = guild.get_channel(cfg["cat_suporte"])

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                inter.user: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                ),
                guild.get_role(cfg["cargo_owner"]): discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True
                )
            }

            canal = await guild.create_text_channel(
                name=f"🆙-{inter.user.name}",
                category=categoria,
                overwrites=overwrites
            )

            emb = discord.Embed(
                title="💳 Pagamento PIX",
                description=(
                    f"Produto: **{data['label']}**\n"
                    f"Valor: **{data['preco']}**\n\n"
                    f"Pix: `{cfg['pix']}`\n\n"
                    "📢 **ENVIE O COMPROVANTE AQUI!**"
                ),
                color=discord.Color.blue()
            )

            await canal.send(
                content=inter.user.mention,
                embed=emb,
                view=AdminActions(inter.user.id, data["label"])
            )

            await inter.response.send_message(f"✅ Carrinho criado: {canal.mention}", ephemeral=True)

        button.callback = abrir
        view = discord.ui.View()
        view.add_item(button)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# ================== BOT ==================
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        try:
            await self.tree.sync()
            print("✅ Slash commands sincronizados globalmente")
        except Exception as e:
            print(f"❌ Erro ao sincronizar: {e}")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"✅ Bot online como {bot.user}")

# ================== COMANDOS ==================
@bot.tree.command(name="setup", description="Configura PIX e Admin")
async def setup(interaction: discord.Interaction, pix: str, cargo_admin: discord.Role, categoria: discord.CategoryChannel):
    db["config"].update({
        "pix": pix,
        "cargo_owner": cargo_admin.id,
        "cat_suporte": categoria.id
    })
    save_db(db)
    await interaction.response.send_message("✅ Configurado com sucesso!", ephemeral=True)

@bot.tree.command(name="produup", description="Menu de pacotes de salas")
async def produup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="SALAS AUTOMATICAS! - GB STORE",
        description="Selecione o pacote desejado no menu abaixo para prosseguir com a compra.",
        color=discord.Color.blue()
    )
    embed.set_image(
        url="https://cdn.discordapp.com/attachments/1447763890225287269/1455736408898797729/ChatGPT_Image_30_de_dez._de_2025_22_36_10.png"
    )
    await interaction.response.send_message(embed=embed, view=ProduUpView())

bot.run(TOKEN)
