"""NOVA Streamlit chatbot powered by Groq."""
from __future__ import annotations
import json, os, re, time
from datetime import datetime, timezone
from typing import Any
import streamlit as st
from groq import APIConnectionError, APIStatusError, AuthenticationError, BadRequestError, Groq, RateLimitError

APP_NAME="NOVA"; FOOTER_TEXT="Built by Arooba Hanif | Corvit Rawalpindi | Powered by Groq"; SHARED_KEY_MESSAGE_LIMIT=15
FALLBACK_MODELS=["llama-3.3-70b-versatile","llama-3.1-8b-instant","openai/gpt-oss-120b","openai/gpt-oss-20b","qwen/qwen3-32b"]
DEFAULT_SETTINGS={"temperature":.7,"max_tokens":1024,"top_p":1.0,"seed":None,"streaming":True,"memory":True,"context_messages":12}
PERSONAS={"Study Buddy":"You are a patient, encouraging study buddy. Explain concepts clearly, use examples, and ask helpful check-in questions.","Code Reviewer":"You are a meticulous senior code reviewer. Identify bugs, security issues, maintainability concerns, and give actionable fixes.","Data Science Mentor":"You are a practical data science mentor. Explain assumptions, recommend sound methods, and communicate insights clearly.","Creative Writer":"You are an imaginative creative writing partner. Offer vivid language, strong structure, and constructive ideas.","Interview Coach":"You are a supportive interview coach. Ask realistic questions, critique answers, and give specific advice.","Roman Urdu and English Helper":"You help naturally in English and Roman Urdu. Match the user's language and explain difficult terms simply.","Custom":"You are a helpful, accurate, and thoughtful AI assistant."}
STARTERS=["Explain a difficult concept simply","Review my Python code","Help me plan a study session","Brainstorm a creative idea"]

def redact_secrets(text:str)->str:
    """Hide Groq keys from user-visible text."""
    return re.sub(r"gsk_[A-Za-z0-9_-]+","gsk_••••••••",str(text))

def init_state()->None:
    """Initialize session state."""
    values={"chats":{"NOVA Chat":[]},"active_chat":"NOVA Chat","models":FALLBACK_MODELS.copy(),"connected":False,"connection_error":"","typed_key":"","shared_messages":0,"settings":DEFAULT_SETTINGS.copy(),"persona":"Study Buddy","system_prompt":PERSONAS["Study Buddy"],"current_model":FALLBACK_MODELS[0]}
    for key,value in values.items(): st.session_state.setdefault(key,value)

def build_css()->str:
    """Return the app CSS."""
    return """<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root{--bg:#0B0B0F;--surface:#121218;--border:rgba(255,255,255,.1);--text:#F7F5F2;--muted:#9D9AA5;--crimson:#E11D48;--gold:#F5B301}html,body,[class*=css]{font-family:Inter,sans-serif;color:var(--text)}.stApp{background:radial-gradient(circle at 70% -10%,rgba(225,29,72,.13),transparent 32%),var(--bg)}[data-testid=stSidebar]{background:rgba(14,14,20,.9);border-right:1px solid var(--border);backdrop-filter:blur(16px)}[data-testid=stSidebar]:before{content:"";display:block;position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--crimson),var(--gold))}[data-testid=stSidebar] .block-container{padding:1.5rem 1.25rem 2rem}h1,h2,h3{font-family:'Space Grotesk',sans-serif}.nova-title{font:700 clamp(3rem,8vw,5.8rem)/.9 'Space Grotesk',sans-serif;letter-spacing:-.08em;background:linear-gradient(100deg,var(--crimson),#ff5578,var(--gold));-webkit-background-clip:text;color:transparent;background-size:200% auto;animation:shine 5s linear infinite}.nova-subtitle{color:var(--muted);margin-top:.8rem;font-size:1.05rem}.hero{text-align:center;padding:8vh 1rem 4vh}.section-title{color:#d7d3d8;font:600 .72rem 'Space Grotesk';letter-spacing:.14em;text-transform:uppercase;margin:1.4rem 0 .55rem}.status-pill{display:inline-flex;padding:.27rem .62rem;border-radius:999px;font-size:.72rem;font-weight:600;background:rgba(245,179,1,.13);color:#ffd96b;border:1px solid rgba(245,179,1,.35)}.status-pill.ok{background:rgba(34,197,94,.12);color:#86efac;border-color:rgba(34,197,94,.35)}[data-testid=stChatMessage]{border:1px solid var(--border);border-radius:20px;padding:.75rem 1rem;margin:.7rem 0;animation:fadein .35s ease both;background:rgba(18,18,24,.72)}[data-testid=stChatInput]{border-radius:24px}[data-testid=stChatInput]:focus-within{box-shadow:0 0 0 1px var(--crimson),0 0 24px rgba(225,29,72,.3)}button,[data-baseweb=select]>div,textarea,input{border-radius:12px!important}button:hover{transform:translateY(-1px);border-color:var(--crimson)!important}[data-baseweb=select]>div{background:#181821;border-color:var(--border)}[data-testid=stExpander]{border-color:var(--border);background:rgba(255,255,255,.02)}footer{visibility:hidden}#MainMenu{visibility:hidden}::-webkit-scrollbar{width:7px}::-webkit-scrollbar-thumb{background:#34343d;border-radius:99px}@keyframes shine{to{background-position:200% center}}@keyframes fadein{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}@media(max-width:768px){.hero{padding:5vh .25rem 2vh}[data-testid=stChatMessage]{width:100%;border-radius:16px}.nova-title{font-size:3.8rem}}@media(prefers-reduced-motion:reduce){*,*:before,*:after{animation:none!important;transition:none!important}}</style>"""

def key_from_sources()->tuple[str,str]:
    """Resolve typed, secret, then environment key."""
    typed=str(st.session_state.get("typed_key","")).strip()
    if typed:return typed,"typed"
    try: secret=str(st.secrets.get("GROQ_API_KEY","")).strip()
    except Exception: secret=""
    if secret:return secret,"shared"
    return os.getenv("GROQ_API_KEY","").strip(),"environment"

def validate_key(key:str)->tuple[bool,str]:
    """Validate a key using the models endpoint."""
    if not key:return False,"No API key found. Add one in the sidebar or configure secrets."
    try: Groq(api_key=key).models.list(); return True,"Connection verified"
    except AuthenticationError:return False,"Authentication failed. Check that the Groq key is valid."
    except (APIConnectionError,TimeoutError):return False,"Could not reach Groq. Check your network connection."
    except Exception as exc:return False,f"Connection test failed: {redact_secrets(exc)}"

def fetch_models(key:str)->list[str]:
    """Fetch live chat-capable models with a safe fallback."""
    try:
        excluded=("whisper","orpheus","tts","guard","safeguard")
        found=[str(x.id) for x in Groq(api_key=key).models.list().data if not any(y in str(x.id).lower() for y in excluded)]
        return sorted(found) or FALLBACK_MODELS.copy()
    except Exception:return FALLBACK_MODELS.copy()

def build_messages(history:list[dict[str,Any]],system_prompt:str,memory:bool,context_messages:int,latest_user:str|None=None)->list[dict[str,str]]:
    """Build the system plus bounded conversation payload."""
    result=[{"role":"system","content":system_prompt}]
    if memory: result += [{"role":x["role"],"content":x["content"]} for x in history[-context_messages:]]
    elif latest_user is not None: result.append({"role":"user","content":latest_user})
    return result

def export_txt(messages:list[dict[str,Any]])->str:return "\n\n".join(f"{x['role'].upper()}: {x['content']}" for x in messages)
def export_json(messages:list[dict[str,Any]],model:str,settings:dict[str,Any],created_at:str|None=None)->str:return json.dumps({"created_at":created_at or datetime.now(timezone.utc).isoformat(),"model":model,"settings":settings,"messages":messages},indent=2,ensure_ascii=False)
def export_markdown(messages:list[dict[str,Any]],model:str)->str:return "# NOVA Chat\n\nModel: `"+model+"`\n\n"+"\n".join(f"## {x['role'].title()}\n\n{x['content']}\n" for x in messages)

def request_args(settings:dict[str,Any],model:str,messages:list[dict[str,str]],stream:bool)->dict[str,Any]:
    args={"model":model,"messages":messages,"temperature":settings["temperature"],"max_completion_tokens":settings["max_tokens"],"top_p":settings["top_p"],"stream":stream}
    if settings.get("seed") is not None:args["seed"]=settings["seed"]
    return args

def make_meta(model:str,usage:Any,elapsed:float,fallback:int)->dict[str,Any]:
    tokens=getattr(usage,"completion_tokens",None) or fallback
    return {"model":model,"elapsed":round(elapsed,2),"tokens":tokens,"tps":round(tokens/elapsed,1) if elapsed else 0}

def ask_groq(key:str,model:str,messages:list[dict[str,str]],settings:dict[str,Any])->tuple[str,dict[str,Any]]:
    """Call Groq with one compatibility retry for unsupported token naming."""
    client=Groq(api_key=key); started=time.perf_counter(); stream=bool(settings["streaming"]); args=request_args(settings,model,messages,stream)
    try: response=client.chat.completions.create(**args)
    except BadRequestError as exc:
        if "max_completion_tokens" not in str(exc).lower() and "unsupported" not in str(exc).lower():raise
        args.pop("max_completion_tokens",None); response=client.chat.completions.create(**args); st.caption("A model-specific setting was skipped and the request was retried.")
    if stream:
        text=""; usage=None
        for chunk in response:
            piece=getattr(chunk.choices[0].delta,"content",None) if chunk.choices else None
            if piece:text+=piece
            usage=getattr(chunk,"usage",None) or usage
        return re.sub(r"<think>.*?</think>","",text,flags=re.I|re.S).strip(),make_meta(model,usage,time.perf_counter()-started,len(text.split()))
    text=response.choices[0].message.content or ""; text=re.sub(r"<think>.*?</think>","",text,flags=re.I|re.S).strip()
    return text,make_meta(model,getattr(response,"usage",None),time.perf_counter()-started,len(text.split()))

def error_message(exc:Exception)->str:
    """Map SDK errors to friendly messages."""
    if isinstance(exc,AuthenticationError):return "Groq rejected the API key. Check it in the sidebar and try again."
    if isinstance(exc,RateLimitError):return "Groq rate limit reached. Wait a moment or use your own key."
    if isinstance(exc,APIConnectionError):return "Groq could not be reached. Check your internet connection."
    if isinstance(exc,BadRequestError):return "The request was not accepted. Check the model ID and settings."
    if isinstance(exc,APIStatusError):
        if exc.status_code==404:return "That model is no longer available on Groq. Click Test connection to refresh the live model list, then choose an available model."
        return f"Groq returned an API error ({exc.status_code}). Try again shortly."
    return f"Something went wrong: {redact_secrets(exc)}"

def render_sidebar()->None:
    """Render controls and safe exports."""
    with st.sidebar:
        st.markdown("<div class='section-title'>NOVA CONTROL ROOM</div>",unsafe_allow_html=True)
        st.text_input("Groq API key",type="password",key="typed_key",placeholder="gsk_…")
        key,source=key_from_sources(); st.caption(f"Active key: {'••••'+key[-4:] if len(key)>=4 else 'not set'} ({'your key' if source=='typed' else source})")
        if st.button("Test connection",use_container_width=True):
            ok,msg=validate_key(key); st.session_state.connected=ok; st.session_state.connection_error=msg
            if ok:st.session_state.models=fetch_models(key)
        cls="status-pill ok" if st.session_state.connected else "status-pill"; st.markdown(f"<span class='{cls}'>● {'Connected' if st.session_state.connected else 'Not connected'}</span>",unsafe_allow_html=True)
        if st.session_state.connection_error:st.caption(st.session_state.connection_error)
        st.markdown("<div class='section-title'>MODEL</div>",unsafe_allow_html=True)
        selected=st.selectbox("Model",st.session_state.models,label_visibility="collapsed"); custom=st.text_input("Custom model ID",placeholder="Optional override"); st.session_state.current_model=custom.strip() or selected
        st.markdown("<div class='section-title'>PERSONA</div>",unsafe_allow_html=True)
        persona=st.selectbox("Persona",list(PERSONAS),key="persona")
        if persona!=st.session_state.get("persona_previous"):st.session_state.system_prompt=PERSONAS[persona];st.session_state.persona_previous=persona
        st.text_area("System prompt",key="system_prompt",height=110)
        st.markdown("<div class='section-title'>GENERATION</div>",unsafe_allow_html=True); s=st.session_state.settings
        s["temperature"]=st.slider("Temperature",0.,2.,s["temperature"],.1);s["max_tokens"]=st.slider("Max response tokens",128,8192,s["max_tokens"],128);s["top_p"]=st.slider("Top P",.1,1.,s["top_p"],.05);seed=st.number_input("Seed (0 = off)",0,2147483647,s["seed"] or 0);s["seed"]=int(seed) or None;s["streaming"]=st.toggle("Streaming",s["streaming"]);s["memory"]=st.toggle("Conversation memory",s["memory"]);s["context_messages"]=st.slider("Recent messages in context",2,30,s["context_messages"])
        st.markdown("<div class='section-title'>CHATS</div>",unsafe_allow_html=True)
        if st.button("＋ New chat",use_container_width=True):
            name=f"Chat {len(st.session_state.chats)+1}";st.session_state.chats[name]=[];st.session_state.active_chat=name;st.rerun()
        st.selectbox("Current chat",list(st.session_state.chats),key="active_chat");c1,c2=st.columns(2)
        if c1.button("Clear",use_container_width=True):st.session_state.chats[st.session_state.active_chat]=[];st.rerun()
        if c2.button("Reset",use_container_width=True):st.session_state.settings=DEFAULT_SETTINGS.copy();st.session_state.persona="Study Buddy";st.session_state.system_prompt=PERSONAS["Study Buddy"];st.rerun()
        messages=st.session_state.chats[st.session_state.active_chat];st.markdown("<div class='section-title'>EXPORT</div>",unsafe_allow_html=True);st.download_button("TXT",export_txt(messages),"nova-chat.txt",use_container_width=True);st.download_button("JSON",export_json(messages,st.session_state.current_model,s),"nova-chat.json","application/json",use_container_width=True);st.download_button("Markdown",export_markdown(messages,st.session_state.current_model),"nova-chat.md","text/markdown",use_container_width=True);st.caption(FOOTER_TEXT)

def render_chat()->None:
    """Render history and empty state controls."""
    messages=st.session_state.chats[st.session_state.active_chat]
    if not messages:
        st.markdown("<div class='hero'><div class='nova-title'>NOVA</div><div class='nova-subtitle'>A focused space for curious minds.</div></div>",unsafe_allow_html=True);cols=st.columns(2)
        for i,prompt in enumerate(STARTERS):
            if cols[i%2].button(prompt,use_container_width=True,key=f"starter-{i}"):st.session_state.pending_prompt=prompt;st.rerun()
    for item in messages:
        with st.chat_message(item["role"],avatar="✦" if item["role"]=="assistant" else "◎"):
            st.markdown(item["content"])
            if item["role"]=="assistant" and item.get("meta"):
                m=item["meta"];st.caption(f"{m['model']} · {m['elapsed']}s · {m['tokens']} tokens · {m['tps']} tok/s")
    if messages and messages[-1]["role"]=="assistant":
        c1,c2=st.columns(2)
        if c1.button("↻ Regenerate",use_container_width=True):st.session_state.regenerate=True;st.rerun()
        if c2.button("Delete last exchange",use_container_width=True):messages.pop();messages.pop() if messages and messages[-1]["role"]=="user" else None;st.rerun()

def handle_prompt(prompt:str)->None:
    """Send a prompt with shared-key protection."""
    key,source=key_from_sources()
    if not key:st.warning("Add a Groq API key in the sidebar to start chatting.");return
    if source=="shared" and st.session_state.shared_messages>=SHARED_KEY_MESSAGE_LIMIT:st.info("This shared demo key has reached its 15-message limit. Enter your own free Groq key in the sidebar to continue.");return
    messages=st.session_state.chats[st.session_state.active_chat];s=st.session_state.settings;prompt_history=messages.copy()
    if st.session_state.get("regenerate") and prompt_history and prompt_history[-1]["role"]=="assistant":prompt_history.pop();prompt=prompt_history.pop()["content"];st.session_state.regenerate=False
    api_messages=build_messages(prompt_history,st.session_state.system_prompt,s["memory"],s["context_messages"],prompt);messages.append({"role":"user","content":prompt,"timestamp":datetime.now(timezone.utc).isoformat()})
    try:
        text,meta=ask_groq(key,st.session_state.current_model,api_messages,s)
        if s["streaming"]:st.write_stream(iter([text]))
        else:st.markdown(text)
        messages.append({"role":"assistant","content":text,"meta":meta,"timestamp":datetime.now(timezone.utc).isoformat()});st.session_state.shared_messages+=source=="shared";st.rerun()
    except Exception as exc:
        messages.pop()
        if isinstance(exc,APIStatusError) and exc.status_code==404:
            refreshed=fetch_models(key)
            if refreshed != FALLBACK_MODELS:
                st.session_state.models=refreshed
                st.session_state.current_model=refreshed[0]
                st.info(f"The selected model is unavailable. Live models were refreshed; NOVA selected `{refreshed[0]}`. Send your message again.")
        else:
            st.error(error_message(exc))

def main()->None:
    """Run NOVA."""
    st.set_page_config(page_title="NOVA · Groq Chat",page_icon="✦",layout="wide",initial_sidebar_state="expanded");init_state();st.markdown(build_css(),unsafe_allow_html=True);render_sidebar();render_chat();prompt=st.chat_input("Ask NOVA anything…");prompt=st.session_state.pop("pending_prompt",None) or prompt
    if prompt:handle_prompt(prompt)

if __name__=="__main__":main()
