# app.py
import gradio as gr
from main import app as fastapi_app


with gr.Blocks() as demo:
    gr.Markdown(
        """
        # 🚀 AI-Powered Deployment API
        
        This Space hosts an automated deployment API.
        
        ## How to Use
        Send a `POST` request to the `/api/handle_task` endpoint.
        
        See the [GitHub Repository](https://github.com/<YOUR_USERNAME>/<YOUR_REPO_NAME>) for detailed documentation and usage examples.
        """
    )

# Mount the FastAPI app to the Gradio interface.
app = gr.mount_gradio_app(fastapi_app, demo, path="/")
