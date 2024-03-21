import base64
from io import BytesIO

import gradio as gr

from transformers import AutoProcessor, Blip2ForConditionalGeneration
import torch

from modules import chat, shared, ui_chat
from modules.ui import gather_interface_values
from modules.utils import gradio

input_hijack = {
    'state': False,
    'value': ["", ""]
}

processor = AutoProcessor.from_pretrained("Salesforce/blip2-opt-2.7b")
model = Blip2ForConditionalGeneration.from_pretrained("Salesforce/blip2-opt-2.7b", torch_dtype=torch.float16)

device = "cpu"
model.to(device)

def chat_input_modifier(text, visible_text, state):
    global input_hijack
    if input_hijack['state']:
        input_hijack['state'] = False
        return input_hijack['value']
    else:
        return text, visible_text
    

def caption_image(raw_image):
    inputs = processor(raw_image, return_tensors="pt").to(device, torch.float16)
    out = model.generate(**inputs, max_new_tokens=100)
    return processor.batch_decode(out, skip_special_tokens=True)[0].strip()

def generate_chat_picture(picture, name1, name2):
    text = f'*{name1} sends {name2} a picture that contains the following: “{caption_image(picture)}”*'
    # lower the resolution of sent images for the chat, otherwise the log size gets out of control quickly with all the base64 values in visible history
    picture.thumbnail((300, 300))
    buffer = BytesIO()
    picture.save(buffer, format="JPEG")
    img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
    visible_text = f'<img src="data:image/jpeg;base64,{img_str}" alt="{text}">'
    return text, visible_text

def ui():
    picture_select = gr.Image(label='Send a picture', type='pil')
    # Prepare the input hijack, update the interface values, call the generation function, and clear the picture
    picture_select.upload(
        lambda picture, name1, name2: input_hijack.update({
            "state": True,
            "value": generate_chat_picture(picture, name1, name2)
        }), [picture_select, shared.gradio['name1'], shared.gradio['name2']], None).then(
        gather_interface_values, gradio(shared.input_elements), gradio('interface_state')).then(
        chat.generate_chat_reply_wrapper, gradio(ui_chat.inputs), gradio('display', 'history'), show_progress=False).then(
        lambda: None, None, picture_select, show_progress=False)