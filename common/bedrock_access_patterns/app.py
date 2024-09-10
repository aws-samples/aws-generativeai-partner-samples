from typing import Callable
from botocore.exceptions import ClientError
import mesop as me
import re
import yaml

# Load configuration from YAML file
with open("config.local.yaml", "r") as f:
    config = yaml.safe_load(f)


def is_localhost_endpoint(api_endpoint):
    pattern = r'^http?://localhost:11434/v1$'
    return bool(re.match(pattern, api_endpoint))

@me.stateclass
class State:
  title: str = "Bedrock Access Patterns"
  # Prompt / Response
  input: str
  response: str
  # Tab open/close
  prompt_tab: bool = True
  response_tab: bool = True
  
  # AWS Config
  selected_option: str = "Customer LLM Gateway"
  access_key: str = config.get("access_key")
  secret_access_key : str = config.get("secret_access_key")
  bedrock_iam_role: str = config.get("bedrock_iam_role")
  customer_account_id: str = config.get("customer_account_id")
  external_id: str = config.get("external_id")
  
  # Model configs
  selected_model: str = config.get("selected_model")
  api_endpoint: str = config.get("api_endpoint")
  api_key: str = config.get("api_key")
  
  # Modal
  modal_open: bool = False
  # Workaround for clearing inputs
  clear_prompt_count: int = 0
  clear_sequence_count: int = 0


@me.page(
  security_policy=me.SecurityPolicy(
    allowed_iframe_parents=["https://google.github.io"],
    dangerously_disable_trusted_types=True
  ),
  path="/",
  title="Bedrock Access Patterns",
)

def page():
  state = me.state(State)

  # Modal
  with modal(modal_open=state.modal_open):
    me.text("Get code", type="headline-5")
    if "Customer LLM Gateway" in state.selected_option:
      me.text(
        "Use the following code in your application to request a model response."
      )
      with me.box(style=_STYLE_CODE_BOX):
        me.markdown(
          _GPT_CODE_TEXT.format(
            content=state.input.replace('"', '\\"'),
            model=state.selected_model,
            api_endpoint= state.api_endpoint,
            api_key=state.api_key,
            # region=state.selected_region,
            # stop_sequences=make_stop_sequence_str(state.stop_sequences),
            # token_limit=state.token_limit,
            # temperature=state.temperature,
          )
        )
    elif "Cross Account Role" or "ISV LLM Gateway" in state.selected_option:
      me.text(
        "Use the following code in your application to request a model response."
      )
      with me.box(style=_STYLE_CODE_BOX):
        me.markdown(
          _CROSS_ACCCOUNT_CODE_TEXT.format(
            # content=state.input.replace('"', '\\"'),
            selected_model=state.selected_model,
            # access_key=state.access_key,
            # secret_access_key=state.secret_access_key,
            bedrock_iam_role=state.bedrock_iam_role,
            customer_account_id=state.customer_account_id,
            external_id=state.external_id,
            input = state.input,
            final_response = "",
            assistant_message = ""
            # api_endpoint= state.api_endpoint,
            # api_key=state.api_key,
            # region=state.selected_region,
            # stop_sequences=make_stop_sequence_str(state.stop_sequences),
            # token_limit=state.token_limit,
            # temperature=state.temperature,
          )
        )
    elif "IAM User" in state.selected_option:
      me.text(
        "Use the following code in your application to request a model response."
      )
      with me.box(style=_STYLE_CODE_BOX):
        me.markdown(
          _IAM_CODE_TEXT.format(
            content=state.input.replace('"', '\\"'),
            selected_model=state.selected_model,
            api_endpoint= state.api_endpoint,
            api_key=state.api_key,
            # region=state.selected_region,
            # stop_sequences=make_stop_sequence_str(state.stop_sequences),
            # token_limit=state.token_limit,
            # temperature=state.temperature,
          )
        )
    else:
      me.text(
        "You can use the following code to start integrating your current prompt and settings into your application."
      )
    me.button(label="Close", type="raised", on_click=on_click_modal)

  # Main content
  with me.box(style=_STYLE_CONTAINER):
    # Main Header
    with me.box(style=_STYLE_MAIN_HEADER):
      with me.box(style=_STYLE_TITLE_BOX):
        me.text(
          state.title,
          type="headline-6",
          style=me.Style(line_height="24px", margin=me.Margin(bottom=0)),
        )

    # Toolbar Header
    with me.box(style=_STYLE_CONFIG_HEADER):
      icon_button(
        icon="code", tooltip="Code", label="CODE", on_click=on_click_show_code
      )

    # Main Content
    with me.box(style=_STYLE_MAIN_COLUMN):
      # Prompt Tab
      with tab_box(header="Prompt", key="prompt_tab"):
        me.textarea(
          label="Write your prompt here and then click Submit",
          # Workaround: update key to clear input.
          key=f"prompt-{state.clear_prompt_count}",
          on_input=on_prompt_input,
          style=_STYLE_INPUT_WIDTH,
        )
        me.button(label="Submit", type="flat", on_click=on_click_submit)
        me.button(label="Clear", on_click=on_click_clear)

      # Response Tab
      with tab_box(header="Response", key="response_tab"):
        if state.response:
          me.markdown(state.response)
        else:
          me.markdown(
            "The model will generate a response after you click Submit."
          )
    
    
    # LLM Config
    with me.box(style=_STYLE_CONFIG_COLUMN):
      me.select(
        options=[
          me.SelectOption(label="Customer LLM Gateway", value="Customer LLM Gateway"),
          me.SelectOption(label="Cross Account Role", value="Cross Account Role"),
          me.SelectOption(label="IAM User", value="IAM User"),
          me.SelectOption(label="ISV LLM Gateway", value="ISV LLM Gateway"),
        ],
        label="Integration Option",
        style=_STYLE_INPUT_WIDTH,
        on_selection_change=on_option_select,
        value=state.selected_option,
      )
      
      if "Customer LLM Gateway" in state.selected_option:
        me.input(
          label="API Endpoint",
          style=_STYLE_INPUT_WIDTH,
          type="url",
          on_input=on_api_change,
          value=state.api_endpoint,
        )
        me.input(
          label="API Key",
          style=_STYLE_INPUT_WIDTH,
          type="password",
          on_input=on_key_change,
          value=state.api_key,
        )
      
      elif "Cross Account Role" in state.selected_option:
        me.input(
          label="Bedrock IAM Role",
          style=_STYLE_INPUT_WIDTH,
          on_input=on_role_change,
          value=state.bedrock_iam_role,
        )
        
        me.input(
          label="Bedrock Account Number",
          style=_STYLE_INPUT_WIDTH,
          on_input=on_account_number_change,
          value=state.customer_account_id,
        )
        
        me.input(
          label="External Id",
          style=_STYLE_INPUT_WIDTH,
          on_input=on_external_id_change,
          value=state.external_id,
        )
      
      elif "IAM User" in state.selected_option:
        me.input(
          label="Access Key",
          style=_STYLE_INPUT_WIDTH,
          on_input=on_access_key_change,
          value=state.access_key,
        )
        me.input(
          label="Secret Access Key",
          style=_STYLE_INPUT_WIDTH,
          type="password",
          on_input=on_secret_key_change,
          value=state.secret_access_key,
        )
      elif "ISV LLM Gateway" in state.selected_option:
        me.input(
          label="Bedrock IAM Role",
          style=_STYLE_INPUT_WIDTH,
          # on_selection_change=on_option_select,
          value=state.bedrock_iam_role,
        )
        
        me.input(
          label="Bedrock Account Number",
          style=_STYLE_INPUT_WIDTH,
          # on_selection_change=on_option_select,
          value=state.customer_account_id,
        )
        
        me.input(
          label="External Id",
          style=_STYLE_INPUT_WIDTH,
          on_input=on_account_number_change,
          value=state.external_id,
        )
      
      model_options=[]
      
      if is_localhost_endpoint(state.api_endpoint):
        model_options.clear()
        model_options.append(me.SelectOption(label="LLama3-8b", value="llama3:8b"))
        model_options.append(me.SelectOption(label="Gemma3-7b", value="gemma:7b"))
      if not is_localhost_endpoint(state.api_endpoint) or "Gateway" not in state.selected_option:
        model_options.clear()
        model_options.append(me.SelectOption(label="Haiku", value="anthropic.claude-3-haiku-20240307-v1:0"))
        model_options.append(me.SelectOption(label="Sonnet", value="anthropic.claude-3-sonnet-20240229-v1:0"))
        model_options.append(me.SelectOption(label="Mistral", value="mistral.mistral-large-2402-v1:0"))
        model_options.append(me.SelectOption(label="Llama3-70b", value="meta.llama3-70b-instruct-v1:0"))
        model_options.append(me.SelectOption(label="Mistral-8x7", value="mistral.mixtral-8x7b-instruct-v0:1"))
        # anthropic.claude-instant-v1
        # anthropic.claude-v2:1
        # anthropic.claude-v2
        # anthropic.claude-3-opus-20240229-v1:0
        # anthropic.claude-3-sonnet-20240229-v1:0
        # anthropic.claude-3-haiku-20240307-v1:0
        # meta.llama2-13b-chat-v1
        # meta.llama2-70b-chat-v1
        # meta.llama3-8b-instruct-v1:0
        # meta.llama3-70b-instruct-v1:0
        # mistral.mistral-7b-instruct-v0:2
        # mistral.mixtral-8x7b-instruct-v0:1

      me.select(
          options=model_options,
          label="Model",
          style=_STYLE_INPUT_WIDTH,
          on_selection_change=on_model_select,
          value=state.selected_model,
      )

# HELPER COMPONENTS


@me.component
def icon_button(*, icon: str, label: str, tooltip: str, on_click: Callable):
  """Icon button with text and tooltip."""
  with me.content_button(on_click=on_click):
    with me.tooltip(message=tooltip):
      with me.box(style=me.Style(display="flex")):
        me.icon(icon=icon)
        me.text(
          label, style=me.Style(line_height="24px", margin=me.Margin(left=5))
        )


@me.content_component
def tab_box(*, header: str, key: str):
  """Collapsible tab box"""
  state = me.state(State)
  tab_open = getattr(state, key)
  with me.box(style=me.Style(width="100%", margin=me.Margin(bottom=20))):
    # Tab Header
    with me.box(
      key=key,
      on_click=on_click_tab_header,
      style=me.Style(padding=_DEFAULT_PADDING, border=_DEFAULT_BORDER),
    ):
      with me.box(style=me.Style(display="flex")):
        me.icon(
          icon="keyboard_arrow_down" if tab_open else "keyboard_arrow_right"
        )
        me.text(
          header,
          style=me.Style(
            line_height="24px", margin=me.Margin(left=5), font_weight="bold"
          ),
        )
    # Tab Content
    with me.box(
      style=me.Style(
        padding=_DEFAULT_PADDING,
        border=_DEFAULT_BORDER,
        display="block" if tab_open else "none",
      )
    ):
      me.slot()


@me.content_component
def modal(modal_open: bool):
  """Basic modal box."""
  with me.box(style=_make_modal_background_style(modal_open)):
    with me.box(style=_STYLE_MODAL_CONTAINER):
      with me.box(style=_STYLE_MODAL_CONTENT):
        me.slot()


# EVENT HANDLERS


def on_click_clear(e: me.ClickEvent):
  """Click event for clearing prompt text."""
  state = me.state(State)
  state.clear_prompt_count += 1
  state.input = ""
  state.response = ""


def on_prompt_input(e: me.InputEvent):
  """Capture prompt input."""
  state = me.state(State)
  state.input = e.value


def on_model_select(e: me.SelectSelectionChangeEvent):
  """Event to select model."""
  state = me.state(State)
  state.selected_model = e.value

def on_option_select(e: me.SelectSelectionChangeEvent):
  """Event to select integration option."""
  state = me.state(State)
  state.selected_option = e.value
  
def on_role_change(e: me.SelectSelectionChangeEvent):
  """Event to select integration option."""
  state = me.state(State)
  state.bedrock_iam_role = e.value
  
def on_account_number_change(e: me.SelectSelectionChangeEvent):
  """Event to select integration option."""
  state = me.state(State)
  state.customer_account_id = e.value

def on_external_id_change(e: me.SelectSelectionChangeEvent):
  """Event to select integration option."""
  state = me.state(State)
  state.external_id = e.value

def on_access_key_change(e: me.SelectSelectionChangeEvent):
  """Event to select integration option."""
  state = me.state(State)
  state.access_key = e.value
  
def on_secret_key_change(e: me.SelectOpenedChangeEvent):
  """Event to select integration option."""
  state = me.state(State)
  state.secret_access_key = e.value
  
def on_api_change(e: me.SelectSelectionChangeEvent):
  """Event to select integration option."""
  state = me.state(State)
  state.api_endpoint = e.value

def on_key_change(e: me.SelectSelectionChangeEvent):
  """Event to select integration option."""
  state = me.state(State)
  state.api_key = e.value


def on_click_add_stop_sequence(e: me.ClickEvent):
  """Save stop sequence. Will create "chip" for the sequence in the input."""
  state = me.state(State)
  if state.stop_sequence:
    state.stop_sequences.append(state.stop_sequence)
    state.clear_sequence_count += 1


def on_click_remove_stop_sequence(e: me.ClickEvent):
  """Click event that removes the stop sequence that was clicked."""
  state = me.state(State)
  index = int(e.key.replace("sequence-", ""))
  del state.stop_sequences[index]


def on_click_tab_header(e: me.ClickEvent):
  """Open and closes tab content."""
  state = me.state(State)
  setattr(state, e.key, not getattr(state, e.key))


def on_click_show_code(e: me.ClickEvent):
  """Opens modal to show generated code for the given model configuration."""
  state = me.state(State)
  state.modal_open = True


def on_click_modal(e: me.ClickEvent):
  """Allows modal to be closed."""
  state = me.state(State)
  if state.modal_open:
    state.modal_open = False


def on_click_submit(e: me.ClickEvent):
  """Submits prompt to test model configuration.

  This example returns canned text. A real implementation
  would call APIs against the given configuration.
  """
  state = me.state(State)
  
  if not state.input.strip():
      state.response = "Please enter a prompt."
      yield
      return
  state.response =""
  for line in transform(state.input):
    state.response += line
    yield

def transform(input: str):
  """Transform function that returns canned responses."""
  
  state = me.state(State)
  try:
    if state.selected_option == "Customer LLM Gateway":
      
      from openai import OpenAI
      client = OpenAI(base_url=state.api_endpoint, api_key=state.api_key)
      completion = client.chat.completions.create(
          model=state.selected_model,
          messages=[{"role": "user", "content": input}],
      )
      yield completion.choices[0].message.content
    
    elif state.selected_option == "Cross Account Role":
      from bedrock_saas_client import BedrockSaaSClient
      
      customer_role_arn = f"arn:aws:iam::{state.customer_account_id}:role/{state.bedrock_iam_role}"
      
      client = BedrockSaaSClient(customer_role_arn, external_id=state.external_id)
      model_id = state.selected_model
      stream = True
      message_list = []
      
      user_message = {
                      "role": "user",
                      "content": [
                          {"text": input}
                      ],
                  }
      message_list.append(user_message)
      
      credentials = client.assume_role()
      # if isinstance(assume_role, str):
      #     yield assume_role
      #     return
      
      try:
          result, message_list = client.invoke_bedrock_model(model_id, input, stream, credentials, message_list)
      except ClientError as e:
          yield str(e)
          return      
      if not stream:
          final_response = result['output']['message']["content"][0]["text"]
          assistant_message = {
              "role": "assistant",
              "content": [
                      {"text": final_response}
                  ],
          }
          message_list.append(assistant_message)
          # print("Assistant: " + final_response)
          yield final_response
      else:
          # print("Assistant: ")
          if result == 'output':
            yield 'Failed to Assume the role'
          assistant_message = ""
          for chunk in result["stream"]:
              if "contentBlockDelta" in chunk:
                  text = chunk["contentBlockDelta"]["delta"]["text"]
                  yield text
                  assistant_message += text
                  # print(text, end="", flush=True)
          assistant_message = {
              "role": "assistant",
              "content": [
                      {"text": assistant_message}
                  ],
          }
          message_list.append(assistant_message)
    
    elif state.selected_option == "IAM User":
      from bedrock_saas_client import BedrockSaaSClient

      
      client = BedrockSaaSClient()
      model_id = state.selected_model
      stream = True
      message_list = []
      
      user_message = {
                      "role": "user",
                      "content": [
                          {"text": input}
                      ],
                  }
      message_list.append(user_message)
      
      credentials = client.get_session_token(state.access_key, state.secret_access_key)
      # if isinstance(assume_role, str):
      #     yield assume_role
      #     return
      
      try:
          result, message_list = client.invoke_bedrock_model(model_id, input, stream, credentials, message_list)
      except ClientError as e:
          yield str(e)
          return      
      if not stream:
          final_response = result['output']['message']["content"][0]["text"]
          assistant_message = {
              "role": "assistant",
              "content": [
                      {"text": final_response}
                  ],
          }
          message_list.append(assistant_message)
          # print("Assistant: " + final_response)
          yield final_response
      else:
          # print("Assistant: ")
          if result == 'output':
            yield 'Failed to Assume the role'
          assistant_message = ""
          for chunk in result["stream"]:
              if "contentBlockDelta" in chunk:
                  text = chunk["contentBlockDelta"]["delta"]["text"]
                  yield text
                  assistant_message += text
                  # print(text, end="", flush=True)
          assistant_message = {
              "role": "assistant",
              "content": [
                      {"text": assistant_message}
                  ],
          }
          message_list.append(assistant_message)
  except Exception as e:
       print(e)
       error_message = f"An error occurred: {e}"
       yield error_message

# HELPERS

_CROSS_ACCCOUNT_CODE_TEXT = """
```python
from bedrock_saas_client import BedrockSaaSClient

customer_role_arn = f"arn:aws:iam::{customer_account_id}:role/{bedrock_iam_role}"

client = BedrockSaaSClient(customer_role_arn, external_id={external_id})
model_id = "{selected_model}"
stream = True
message_list = []

user_message = {{
                "role": "user",
                "content": [
                    "text": input,
                ],
            }}
message_list.append(user_message)

credentials = client.assume_role()
try:
    result, message_list = client.invoke_bedrock_model(model_id, input, stream, credentials, message_list)
except ClientError as e:
    yield str(e)
    return      
if not stream:
    final_response = result['output']['message']["content"][0]["text"]
    assistant_message = {{
        "role": "assistant",
        "content": [
                "text": final_response
            ],
    }}
    message_list.append(assistant_message)
    # print("Assistant: " + final_response)
    yield final_response
else:
    # print("Assistant: ")
    if result == 'output':
    yield 'Failed to Assume the role'
    assistant_message = ""
    for chunk in result["stream"]:
        if "contentBlockDelta" in chunk:
            text = chunk["contentBlockDelta"]["delta"]["text"]
            yield text
            assistant_message += text
            # print(text, end="", flush=True)
    assistant_message = {{
        "role": "assistant",
        "content": [
                "text": assistant_message
            ],
    }}
    message_list.append(assistant_message)
```
""".strip()


_IAM_CODE_TEXT = """
```python
from bedrock_saas_client import BedrockSaaSClient

client = BedrockSaaSClient()
model_id = "{selected_model}"
stream = True
message_list = []

user_message = {{
                "role": "user",
                "content": [
                    "text": input,
                ],
            }}
message_list.append(user_message)

credentials = client.get_session_token(access_key, secret_access_key)
try:
    result, message_list = client.invoke_bedrock_model(model_id, input, stream, credentials, message_list)
except ClientError as e:
    yield str(e)
    return
if not stream:
    final_response = result['output']['message']["content"][0]["text"]
    assistant_message = {{
        "role": "assistant",
        "content": [
                "text": final_response
            ],
    }}
    message_list.append(assistant_message)
    # print("Assistant: " + final_response)
    yield final_response
else:
    # print("Assistant: ")
    if result == 'output':
    yield 'Failed to Assume the role'
    assistant_message = ""
    for chunk in result["stream"]:
        if "contentBlockDelta" in chunk:
            text = chunk["contentBlockDelta"]["delta"]["text"]
            yield text
            assistant_message += text
            # print(text, end="", flush=True)
    assistant_message = {{
        "role": "assistant",
        "content": [
                "text": assistant_message
            ],
    }}
    message_list.append(assistant_message)
```
""".strip()


_GPT_CODE_TEXT = """
```python
from openai import OpenAI
client = OpenAI(base_url="{api_endpoint}", api_key="{api_key}")

response = client.chat.completions.create(
  model="{model}",
  messages=[
    {{
      "role": "user",
      "content": "{content}"
    }}
  ],
)
```
""".strip()


def make_stop_sequence_str(stop_sequences: list[str]) -> str:
  """Formats stop sequences for code output (list of strings)."""
  return ",".join(map(lambda s: f'"{s}"', stop_sequences))


# STYLES


def _make_modal_background_style(modal_open: bool) -> me.Style:
  """Makes style for modal background.

  Args:
    modal_open: Whether the modal is open.
  """
  return me.Style(
    display="block" if modal_open else "none",
    position="fixed",
    z_index=1000,
    width="100%",
    height="100%",
    overflow_x="auto",
    overflow_y="auto",
    background="rgba(0,0,0,0.4)",
  )


_DEFAULT_PADDING = me.Padding.all(15)
_DEFAULT_BORDER = me.Border.all(
  me.BorderSide(color="#e0e0e0", width=1, style="solid")
)

_STYLE_INPUT_WIDTH = me.Style(width="100%")
_STYLE_SLIDER_INPUT_BOX = me.Style(display="flex", flex_wrap="wrap")
_STYLE_SLIDER_WRAP = me.Style(flex_grow=1)
_STYLE_SLIDER_LABEL = me.Style(padding=me.Padding(bottom=10))
_STYLE_SLIDER = me.Style(width="90%")
_STYLE_SLIDER_INPUT = me.Style(width=75)

_STYLE_STOP_SEQUENCE_BOX = me.Style(display="flex")
_STYLE_STOP_SEQUENCE_WRAP = me.Style(flex_grow=1)

_STYLE_CONTAINER = me.Style(
  display="grid",
  grid_template_columns="5fr 2fr",
  grid_template_rows="auto 5fr",
  height="100vh",
)

_STYLE_MAIN_HEADER = me.Style(
  border=_DEFAULT_BORDER, padding=me.Padding.all(15)
)

_STYLE_MAIN_COLUMN = me.Style(
  border=_DEFAULT_BORDER,
  padding=me.Padding.all(15),
  overflow_y="scroll",
)

_STYLE_CONFIG_COLUMN = me.Style(
  border=_DEFAULT_BORDER,
  padding=me.Padding.all(15),
  overflow_y="scroll",
)

_STYLE_TITLE_BOX = me.Style(display="inline-block")

_STYLE_CONFIG_HEADER = me.Style(
  border=_DEFAULT_BORDER, padding=me.Padding.all(10)
)

_STYLE_STOP_SEQUENCE_CHIP = me.Style(margin=me.Margin.all(3))

_STYLE_MODAL_CONTAINER = me.Style(
  background="#fff",
  margin=me.Margin.symmetric(vertical="0", horizontal="auto"),
  width="min(1024px, 100%)",
  box_sizing="content-box",
  height="100vh",
  overflow_y="scroll",
  box_shadow=("0 3px 1px -2px #0003, 0 2px 2px #00000024, 0 1px 5px #0000001f"),
)

_STYLE_MODAL_CONTENT = me.Style(margin=me.Margin.all(30))

_STYLE_CODE_BOX = me.Style(
  font_size=13,
  margin=me.Margin.symmetric(vertical=10, horizontal=0),
  padding=me.Padding.all(10),
  border=me.Border.all(me.BorderSide(color="#e0e0e0", width=1, style="solid")),
)