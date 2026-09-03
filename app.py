import gradio as gr
import subprocess
import threading

def run_bot():
    subprocess.Popen(["python", "main.py"])

threading.Thread(target=run_bot, daemon=True).start()

with gr.Blocks() as demo:
    gr.Markdown("# ?? Hall of Shame Bot is Online!
This Gradio interface keeps the Hugging Face Space running.")

demo.launch()
