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
intents.message_content = True  # Necessário para alguns recursos
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"🔄 Sincronizando comandos...")
    try:
        # Sincroniza os comandos globalmente
        synced = await bot.tree.sync()
        print(f"✅ Bot online como {bot.user}")
        print(f"✅ {len(synced)} comandos sincronizados")
        print(f"📋 Comandos: {[cmd.name for cmd in synced]}")
    except Exception as e:
        print(f"❌ Erro ao sincronizar: {e}")

# ================= VERIFICAÇÃO DE ADMIN =================
def is_admin():
    async def predicate(interaction: discord.Interaction):
        cargo_admin_id = db["config"].get("cargo_admin")
        
        # Se não há cargo configurado, apenas admins do servidor podem usar
        if not cargo_admin_id:
            return interaction.user.guild_permissions.administrator
        
        # Verifica se tem o cargo configurado OU é admin
        has_role = any(role.id == cargo_admin_id for role in interaction.user.roles)
        is_server_admin = interaction.user.guild_permissions.administrator
        
        return has_role or is_server_admin
    
    return app_commands.check(predicate)

# ================= COMANDOS =================
@bot.tree.command(name="configurar", description="Configura PIX, cargo admin e categoria")
@app_commands.describe(
    pix="Chave PIX para pagamentos",
    cargo_admin="Cargo que pode gerenciar o bot",
    categoria="Categoria onde os tickets serão criados"
)
@app_commands.default_permissions(administrator=True)
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
    
    embed = discord.Embed(
        title="✅ Configuração Salva",
        description="As configurações foram atualizadas com sucesso!",
        color=discord.Color.green()
    )
    embed.add_field(name="💳 PIX", value=pix, inline=False)
    embed.add_field(name="👑 Cargo Admin", value=cargo_admin.mention, inline=False)
    embed.add_field(name="📁 Categoria", value=categoria.mention, inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ------------------------------------------------
@bot.tree.command(name="criarproduto", description="Cria um novo produto na loja")
@app_commands.describe(
    nome="Nome do produto",
    preco="Preço (ex: R$ 10,00)",
    descricao="Descrição do produto",
    imagem="URL da imagem do produto (opcional)"
)
@app_commands.default_permissions(administrator=True)
async def criarproduto(
    interaction: discord.Interaction,
    nome: str,
    preco: str,
    descricao: str,
    imagem: str = None
):
    if nome in db["produtos"]:
        await interaction.response.send_message(
            f"⚠️ Produto **{nome}** já existe! Use outro nome.",
            ephemeral=True
        )
        return
    
    db["produtos"][nome] = {
        "preco": preco,
        "descricao": descricao,
        "imagem": imagem
    }
    save_db(db)
    
    embed = discord.Embed(
        title="✅ Produto Criado",
        description=f"O produto **{nome}** foi criado com sucesso!",
        color=discord.Color.green()
    )
    embed.add_field(name="💰 Preço", value=preco, inline=True)
    embed.add_field(name="📝 Descrição", value=descricao, inline=False)
    if imagem:
        embed.set_thumbnail(url=imagem)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ------------------------------------------------
@bot.tree.command(name="listarprodutos", description="Lista todos os produtos cadastrados")
@app_commands.default_permissions(administrator=True)
async def listarprodutos(interaction: discord.Interaction):
    if not db["produtos"]:
        await interaction.response.send_message(
            "📦 Nenhum produto cadastrado ainda.",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title="📦 Produtos Cadastrados",
        description="Lista de todos os produtos disponíveis:",
        color=discord.Color.blue()
    )
    
    for nome, info in db["produtos"].items():
        embed.add_field(
            name=f"🛒 {nome}",
            value=f"**Preço:** {info['preco']}\n**Descrição:** {info['descricao'][:50]}...",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ------------------------------------------------
@bot.tree.command(name="deletarproduto", description="Remove um produto")
@app_commands.describe(nome="Nome do produto a remover")
@app_commands.default_permissions(administrator=True)
async def deletarproduto(interaction: discord.Interaction, nome: str):
    if nome not in db["produtos"]:
        await interaction.response.send_message(
            f"❌ Produto **{nome}** não encontrado.",
            ephemeral=True
        )
        return
    
    del db["produtos"][nome]
    save_db(db)
    
    await interaction.response.send_message(
        f"✅ Produto **{nome}** removido com sucesso!",
        ephemeral=True
    )

# ------------------------------------------------
@bot.tree.command(name="enviarproduto", description="Envia embed de um produto em um canal")
@app_commands.describe(
    nome="Nome do produto",
    canal="Canal onde o produto será enviado",
    mensagem_botao="Texto do botão",
    link_botao="Link do botão (ex: link do WhatsApp)"
)
@app_commands.default_permissions(administrator=True)
async def enviarproduto(
    interaction: discord.Interaction,
    nome: str,
    canal: discord.TextChannel,
    mensagem_botao: str,
    link_botao: str
):
    produto = db["produtos"].get(nome)
    if not produto:
        await interaction.response.send_message(
            f"❌ Produto **{nome}** não encontrado. Use `/listarprodutos` para ver os disponíveis.",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title=f"🛒 {nome}",
        description=produto["descricao"],
        color=discord.Color.blue()
    )
    embed.add_field(name="💰 Preço", value=produto["preco"], inline=False)
    
    if produto["imagem"]:
        embed.set_image(url=produto["imagem"])
    
    embed.set_footer(text="GB STORE • Clique no botão para comprar")
    
    view = discord.ui.View(timeout=None)  # View permanente
    view.add_item(
        discord.ui.Button(
            label=mensagem_botao,
            url=link_botao,
            style=discord.ButtonStyle.link,
            emoji="🛒"
        )
    )
    
    try:
        await canal.send(embed=embed, view=view)
        await interaction.response.send_message(
            f"✅ Produto **{nome}** enviado em {canal.mention}",
            ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            f"❌ Não tenho permissão para enviar mensagens em {canal.mention}",
            ephemeral=True
        )

# ------------------------------------------------
@bot.tree.command(name="ajuda", description="Mostra todos os comandos disponíveis")
async def ajuda(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📚 Comandos do Bot",
        description="Lista de comandos disponíveis:",
        color=discord.Color.purple()
    )
    
    embed.add_field(
        name="⚙️ `/configurar`",
        value="Configura PIX, cargo admin e categoria de tickets",
        inline=False
    )
    embed.add_field(
        name="➕ `/criarproduto`",
        value="Cria um novo produto na loja",
        inline=False
    )
    embed.add_field(
        name="📋 `/listarprodutos`",
        value="Lista todos os produtos cadastrados",
        inline=False
    )
    embed.add_field(
        name="🗑️ `/deletarproduto`",
        value="Remove um produto",
        inline=False
    )
    embed.add_field(
        name="📤 `/enviarproduto`",
        value="Envia embed do produto em um canal",
        inline=False
    )
    embed.add_field(
        name="❓ `/ajuda`",
        value="Mostra esta mensagem",
        inline=False
    )
    
    embed.set_footer(text="GB STORE • Use / para ver os comandos")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ================= START =================
print("🚀 Iniciando bot...")
bot.run(TOKEN)
