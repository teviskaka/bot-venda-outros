import discord
from discord.ext import commands
import json
import os
import sys

# ================= TOKEN =================
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ DISCORD_TOKEN não definido")
    sys.exit(1)

# ================= DATABASE =================
DB_FILE = "database.json"

def load_db():
    if not os.path.exists(DB_FILE):
        return {
            "config": {
                "pix": None,
                "cargo_admin": None,
                "categoria": None
            }
        }
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

db = load_db()

# ================= BOT =================
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Slash commands sincronizados")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"✅ Bot online como {bot.user}")

# ================= SETUP =================
@bot.tree.command(name="setup", description="Configura PIX, cargo admin e categoria")
async def setup(
    interaction: discord.Interaction,
    pix: str,
    cargo_admin: discord.Role,
    categoria: discord.CategoryChannel
):
    db["config"]["pix"] = pix
    db["config"]["cargo_admin"] = cargo_admin.id
    db["config"]["categoria"] = categoria.id
    save_db(db)

    await interaction.response.send_message(
        "✅ **Configuração salva com sucesso!**",
        ephemeral=True
    )

# ================= CRIAR PRODUTO =================
@bot.tree.command(name="criarproduto", description="Cria um carrinho de compra")
async def criarproduto(
    interaction: discord.Interaction,
    cliente: discord.Member,
    produto: str,
    valor: str
):
    cfg = db["config"]

    if not all(cfg.values()):
        return await interaction.response.send_message(
            "❌ Use /setup antes.",
            ephemeral=True
        )

    guild = interaction.guild
    categoria = guild.get_channel(cfg["categoria"])

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        cliente: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True
        ),
        guild.get_role(cfg["cargo_admin"]): discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True
        )
    }

    canal = await guild.create_text_channel(
        name=f"🛒-{cliente.name}",
        category=categoria,
        overwrites=overwrites
    )

    embed = discord.Embed(
        title="🛒 Carrinho Aberto",
        description=(
            f"👤 Cliente: {cliente.mention}\n"
            f"📦 Produto: **{produto}**\n"
            f"💰 Valor: **{valor}**\n\n"
            f"💳 **PIX:** `{cfg['pix']}`\n\n"
            "📨 Envie o comprovante neste canal."
        ),
        color=discord.Color.blue()
    )

    await canal.send(cliente.mention, embed=embed)

    await interaction.response.send_message(
        f"✅ Carrinho criado: {canal.mention}",
        ephemeral=True
    )

# ================= ENVIAR PRODUTO =================
@bot.tree.command(name="enviarproduto", description="Envia o produto para o cliente")
async def enviarproduto(
    interaction: discord.Interaction,
    cliente: discord.Member,
    mensagem: str
):
    if not any(r.id == db["config"]["cargo_admin"] for r in interaction.user.roles):
        return await interaction.response.send_message(
            "❌ Sem permissão.",
            ephemeral=True
        )

    embed = discord.Embed(
        title="📦 Produto Entregue",
        description=mensagem,
        color=discord.Color.green()
    )

    try:
        await cliente.send(embed=embed)
        await interaction.response.send_message(
            "✅ Produto enviado no privado do cliente!",
            ephemeral=True
        )
    except:
        await interaction.response.send_message(
            "❌ Não consegui enviar DM ao cliente.",
            ephemeral=True
        )

bot.run(TOKEN)
