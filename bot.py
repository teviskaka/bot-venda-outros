import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import sys

# ================= TOKEN =================
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ ERRO: DISCORD_TOKEN não definido")
    sys.exit(1)

# ================= DATABASE =================
DB_FILE = "database.json"

def load_db():
    if not os.path.exists(DB_FILE):
        return {
            "config": {
                "pix": "Não configurado",
                "cargo_admin": None,
                "categoria": None
            },
            "produtos": {}
        }
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

db = load_db()

# ================= BOT =================
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bot online como {bot.user}")

# ================= COMANDOS =================

@bot.tree.command(name="configurar", description="Configura PIX, cargo admin e categoria")
async def configurar(
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

# ------------------------------------------------

@bot.tree.command(name="criarproduto", description="Cria um produto")
async def criarproduto(
    interaction: discord.Interaction,
    nome: str,
    preco: str,
    descricao: str,
    imagem: str = None
):
    db["produtos"][nome] = {
        "preco": preco,
        "descricao": descricao,
        "imagem": imagem
    }
    save_db(db)

    await interaction.response.send_message(
        f"✅ Produto **{nome}** criado!",
        ephemeral=True
    )

# ------------------------------------------------

@bot.tree.command(name="enviarproduto", description="Envia embed de um produto")
async def enviarproduto(
    interaction: discord.Interaction,
    nome: str,
    canal: discord.TextChannel,
    mensagem_botao: str,
    link_botao: str
):
    produto = db["produtos"].get(nome)

    if not produto:
        return await interaction.response.send_message(
            "❌ Produto não encontrado.",
            ephemeral=True
        )

    embed = discord.Embed(
        title=f"🛒 {nome}",
        description=produto["descricao"],
        color=discord.Color.blue()
    )
    embed.add_field(name="💰 Preço", value=produto["preco"], inline=False)

    if produto["imagem"]:
        embed.set_image(url=produto["imagem"])

    embed.set_footer(text="GB STORE")

    view = discord.ui.View()
    view.add_item(
        discord.ui.Button(
            label=mensagem_botao,
            url=link_botao,
            style=discord.ButtonStyle.link
        )
    )

    await canal.send(embed=embed, view=view)
    await interaction.response.send_message(
        f"✅ Produto enviado em {canal.mention}",
        ephemeral=True
    )

# ================= START =================
bot.run(TOKEN)
