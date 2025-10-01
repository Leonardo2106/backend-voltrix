import os, json, dataclasses
from django.conf import settings
from django.core.cache import cache
from asgiref.sync import async_to_sync
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from dotenv import load_dotenv
import google.generativeai as genai

from tapo import ApiClient
from apps.tapo.models import Dispositivo

load_dotenv()

API_KEY = getattr(settings, 'GEMINI_API_KEY', os.getenv('GEMINI_API_KEY'))
MODEL   = getattr(settings, 'GEMINI_MODEL',  os.getenv('GEMINI_MODEL', 'gemini-robotics-er-1.5-preview'))
if not API_KEY:
    raise RuntimeError('Defina GEMINI_API_KEY no .env ou settings.')
genai.configure(api_key=API_KEY)

def _first_attr(obj, *names):
    for n in names:
        if hasattr(obj, n):
            v = getattr(obj, n)
            if v is not None:
                return v
    return None

def _to_dict(obj):
    for m in ("model_dump","dict","to_dict","as_dict"):
        if hasattr(obj, m):
            try:
                d = getattr(obj, m)()
                if isinstance(d, dict): return d
            except: pass
    if dataclasses.is_dataclass(obj): return dataclasses.asdict(obj)
    if hasattr(obj, "__dict__"): return {k:v for k,v in obj.__dict__.items() if not k.startswith("_")}
    return {}

def _mw_to_w(x):
    if x is None: return None
    x = float(x); return x/1000.0 if x > 1000 else x

def _wh_to_kwh(x):
    if x is None: return None
    x = float(x); return x/1000.0 if x > 10 else x

async def _read_p110(ip: str, username: str, password: str):
    client = ApiClient(username, password)
    plug = await client.p110(ip)
    e = await plug.get_energy_usage()
    ed = _to_dict(e)

    p = _first_attr(e, "current_power","current_power_w","power","power_w","active_power","power_mw")
    if p is None:
        for k in ("current_power","current_power_w","power","power_w","active_power","power_mw"):
            if ed.get(k) is not None: p = ed[k]; break
    power_w = _mw_to_w(p) if p is not None else None

    t = _first_attr(e, "today_energy","energy_today","today_kwh","today_wh")
    if t is None:
        for k in ("today_energy","energy_today","today_kwh","today_wh"):
            if ed.get(k) is not None: t = ed[k]; break
    today_kwh = _wh_to_kwh(t) if t is not None else None

    m = _first_attr(e, "month_energy","energy_month","month_kwh","month_wh")
    if m is None:
        for k in ("month_energy","energy_month","month_kwh","month_wh"):
            if ed.get(k) is not None: m = ed[k]; break
    month_kwh = _wh_to_kwh(m) if m is not None else None

    info = await plug.get_device_info()
    is_on = _first_attr(info, "device_on","is_on","on","device_on_state")
    name  = _first_attr(info, "nickname","alias","device_name")
    model = _first_attr(info, "model","device_model")

    return {
        "w_instantaneo": power_w,
        "kwh_hoje": today_kwh,
        "kwh_mes": month_kwh,
        "ligado": bool(is_on) if is_on is not None else None,
        "nome": name,
        "modelo": model,
    }

def _refresh_and_cache_energy_for_user(user, dispositivo_id: int | None = None, ttl: int = 30):
    if dispositivo_id:
        disp = Dispositivo.objects.filter(pk=dispositivo_id, owner=user).first()
    else:
        disp = Dispositivo.objects.filter(owner=user).first()
    if not disp or not disp.ip:
        return None, 'Dispositivo não encontrado ou sem IP.'

    TAPO_USER = os.getenv('TAPO_USER')
    TAPO_PASS = os.getenv('TAPO_PASS')
    if not TAPO_USER or not TAPO_PASS:
        return None, 'TAPO_USER/TAPO_PASS ausentes no servidor'

    try:
        data = async_to_sync(_read_p110)(disp.ip, TAPO_USER, TAPO_PASS)
    except Exception as e:
        return None, f'Falha ao ler P110: {e}'

    key = f'energy:last:{user.id}:{disp.id}'
    cache.set(key, data, timeout=ttl)
    return {"device_id": disp.id, "title": disp.title, "ip": disp.ip, **data}, None

def _get_cached_energy(user, dispositivo_id: int | None = None):
    disp = (Dispositivo.objects.filter(pk=dispositivo_id, owner=user).first()
            if dispositivo_id else Dispositivo.objects.filter(owner=user).first())
    if not disp: return None
    key = f"energy:last:{user.id}:{disp.id}"
    return cache.get(key)

class ChatOnceView(APIView):

    def post(self, request):
        body = request.data or {}
        message = (body.get("message") or "").strip()
        if not message:
            return Response({"detail": "Campo 'message' é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

        dispositivo_id = body.get("dispositivo_id")  # opcional
        temperature   = float(body.get("temperature", 0.7))
        top_p         = float(body.get("top_p", 0.95))
        top_k         = int(body.get("top_k", 40))
        max_tokens    = int(body.get("max_output_tokens", 1024))

        snapshot, err = _refresh_and_cache_energy_for_user(
            getattr(request, 'user', None), dispositivo_id=dispositivo_id, ttl=30
        )
        context_line = ''
        if snapshot:
            context_line = (
                f"STATUS[{snapshot['title']}]: "
                f"{(snapshot['w_instantaneo'] or 0):.1f} W agora | "
                f"Hoje: {(snapshot['kwh_hoje'] or 0):.3f} kWh | "
                f"Mês: {(snapshot['kwh_mes'] or 0):.3f} kWh | "
                f"Ligado: {snapshot['ligado']}"
            )
        elif err:
            context_line = f"STATUS: indisponível ({err})"

        system_prompt = body.get('system_prompt') or "Você é o Assistente Virtual da Votrix, responda em PT-BR, técnico e conciso."
        system_prompt += '\nSe o usuário perguntar sobre consumo/energia, use o STATUS abaixo.'
        parts = [
            {"role": "user", "parts": [{"text": f'[SYSTEM]\n{system_prompt}\n{context_line}'}]},
            {"role": "user", "parts": [{"text": message}]},
        ]

        try:
            model = genai.GenerativeModel(MODEL)
            resp = model.generate_content(
                parts,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature, top_p=top_p, top_k=top_k, max_output_tokens=max_tokens
                ),
                safety_settings=None,
            )
        except Exception as e:
            return Response({"detail": f'Erro ao chamar Gemini: {e}'}, status=status.HTTP_502_BAD_GATEWAY)

        text = getattr(resp, "text", "") or ""
        usage = getattr(resp, "usage_metadata", None)
        tokens_in  = getattr(usage, "prompt_token_count", None) if usage else None
        tokens_out = getattr(usage, "candidates_token_count", None) if usage else None

        return Response({
            "output": text,
            # "model": MODEL,
            # "snapshot": snapshot, # detalhes sobre o dispositio
            # "tokens_in": tokens_in, # quantos tokens entraram
            # "tokens_out": tokens_out, # quantos tokes sairam
        }, status=status.HTTP_200_OK)
