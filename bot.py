import discord
from discord.ext import commands, tasks
import aiohttp
import random
import csv
import os
import asyncio
from dotenv import load_dotenv
import cairosvg
from io import BytesIO

load_dotenv()

# Load the token from the environment variable
TOKEN = os.getenv('DISCORD_TOKEN')

if TOKEN is None:
    raise ValueError("The DISCORD_TOKEN environment variable is not set.")

# Path to your CSV file
CSV_PATH = 'C:/Users/User/AppData/Local/Programs/Python/Python39/countries.csv'  # Replace this with the path to your CSV file

# Intents (necessary for bots in newer versions of discord.py)
intents = discord.Intents.default()
intents.message_content = True

# Initialize the bot without a command prefix
bot = commands.Bot(command_prefix="", intents=intents)

# List to hold country names and flag URLs
flags = []

# Track the current country name for guessing
current_country = ""
current_channel_id = None  # To track where the guess game is happening

# Read country names and flag URLs from the CSV file
def load_flag_data():
    global flags
    with open(CSV_PATH, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            if len(row) > 2:  # Ensure there is at least 3 columns
                flags.append((row[0], row[2]))  # (Country name, Flag URL)

# Define an event when the bot is ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    load_flag_data()  # Load flag data when the bot is ready
    post_image.start()  # Start the task to upload the image

# Listen for messages in the text channels
@bot.event
async def on_message(message):
    global current_country, current_channel_id

    if message.author == bot.user:
        return

    if current_country and message.channel.id == current_channel_id and message.content.lower() == current_country.lower():
        await message.channel.send(f"Correct! The answer is **{current_country}**!")
        current_country = ""  # Reset current_country
        current_channel_id = None  # Reset current_channel_id
        return

    await bot.process_commands(message)

# Command to clear messages
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    if amount <= 0:
        await ctx.send("Please specify a positive number of messages to delete.")
        return

    deleted = await ctx.channel.purge(limit=amount)
    await ctx.send(f"Deleted {len(deleted)} message(s).", delete_after=5)

# Function to convert SVG to PNG
async def convert_svg_to_png(svg_bytes):
    png_output = BytesIO()
    cairosvg.svg2png(bytestring=svg_bytes, write_to=png_output)
    png_output.seek(0)
    return png_output

# Task to send a message every 20 seconds
@tasks.loop(seconds=20)
async def post_image():
    global current_country, current_channel_id
    if flags:
        country, url = random.choice(flags)  # Choose a random flag
        current_country = country  # Update the current country name

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    svg_bytes = await response.read()
                    print(url)
                    
                    # Convert SVG to PNG
                    png_image = await convert_svg_to_png(svg_bytes)
                    
                    # Create the embed
                    embed = discord.Embed(
                        title="Guess the Country",
                        description="You have **10 seconds** to guess the country below.",
                        color=0x00FF00  # Green color
                    )
                    embed.set_image(url="attachment://flag.png")

                    # Send the embed message to the specified channel
                    channel = bot.get_channel(1272172313919488055)  # Replace with your channel ID
                    if channel is not None:
                        # Send the converted PNG image
                        await channel.send(embed=embed, file=discord.File(png_image, filename="flag.png"))
                        current_channel_id = channel.id  # Track the channel ID where the game is happening
                    
                    # Wait for 10 seconds for a response
                    await asyncio.sleep(10)
                    
                    if current_country:
                        # Send a follow-up message indicating the answer
                        embed = discord.Embed(
                            title="Time's up!",
                            description=f"No one got it! The answer was **{current_country}**.",
                            color=0xFF0000  # Red color
                        )
                        await channel.send(embed=embed)
                        
                        current_country = ""  # Reset current_country
                        current_channel_id = None  # Reset current_channel_id
                else:
                    print(f"Failed to fetch image. Status code: {response.status}")
    else:
        print("No flag URLs loaded.")

# Run the bot
bot.run(TOKEN)
