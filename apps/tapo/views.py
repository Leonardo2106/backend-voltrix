import os, json, dataclasses
from dotenv import load_dotenv
from pprint import pformat
from asgiref.sync import async_to_sync
from django.shortcuts import get_object_or_404

from django.core.cache import cache

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from tapo import ApiClient
from .models import Dispositivo
from .serializers import DispositivoSerializer

load_dotenv()

def first_attr(obj, *names, default=None):
    for n in names:
        if hasattr(obj, n):
            v = getattr(obj, n)
            if v is not None:
                return v
    return default

def to_dict(obj):
    for m in ("model_dump", "dict", "to_dict", "as_dict"):
        if hasattr(obj, m):
            try:
                d = getattr(obj, m)()
                if isinstance(d, dict):
                    return d
            except:
                pass
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    if hasattr(obj, "json"):
        try:
            return json.loads(obj.json())
        except:
            pass
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    return {"value": str(obj)}

def mw_to_w(x):
    if x is None:
        return None
    x = float(x)
    return x/1000.0 if x > 1000 else x

def wh_to_kwh(x):
    if x is None:
        return None
    x = float(x)
    return x/1000.0 if x > 10 else x

async def _read_p110(ip: str, username: str, password: str):
    client = ApiClient(username, password)
    plug = await client.p110(ip)

    energy = await plug.get_energy_usage()
    edict = to_dict(energy)

    current_power = first_attr(energy, "current_power","current_power_w","power","power_w","active_power","power_mw")
    if current_power is None and isinstance(edict, dict):
        for k in ("current_power","current_power_w","power","power_w","active_power","power_mw"):
            if edict.get(k) is not None:
                current_power = edict[k]; break
    current_power_w = mw_to_w(current_power) if current_power is not None else None

    today_energy = first_attr(energy, "today_energy","energy_today","today_kwh","today_wh")
    if today_energy is None and isinstance(edict, dict):
        for k in ("today_energy","energy_today","today_kwh","today_wh"):
            if edict.get(k) is not None:
                today_energy = edict[k]; break
    today_kwh = wh_to_kwh(today_energy) if today_energy is not None else None

    month_energy = first_attr(energy, "month_energy","energy_month","month_kwh","month_wh")
    if month_energy is None and isinstance(edict, dict):
        for k in ("month_energy","energy_month","month_kwh","month_wh"):
            if edict.get(k) is not None:
                month_energy = edict[k]; break
    month_kwh = wh_to_kwh(month_energy) if month_energy is not None else None

    info = await plug.get_device_info()
    idict = to_dict(info)

    is_on = first_attr(info, 'device_on','is_on','on','device_on_state', default=None)
    model = first_attr(info, 'model','device_model', default=None)
    name  = first_attr(info, 'nickname','alias','device_name', default=None)

    return {
        'dispositivo_info': {
            'ligado': bool(is_on) if is_on is not None else None,
            'modelo': model,
            'nome':   name,
        },
        'energia': {
            'w_instantaneo': current_power_w,
            'kwh_hoje': today_kwh,
            'kwh_mes':  month_kwh,
        },
        'raw': {
            'get_energy_usage': edict,
            'get_device_info':  idict,
        }
    }

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dispositivo(request):
    qs = Dispositivo.objects.filter(owner=request.user)
    return Response(DispositivoSerializer(qs, many=True).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dispositivo_energia(request, pk: int):
    disp = get_object_or_404(Dispositivo, pk=pk, owner=request.user)
    ip = disp.ip
    if not ip:
        return Response({'detail': 'Dispositivo sem IP cadastrado.'}, status=400)

    tapo_user = os.getenv('TAPO_USER')
    tapo_pass = os.getenv('TAPO_PASS')
    if not tapo_user or not tapo_pass:
        return Response({'detail': 'TAPO_USER/TAPO_PASS ausentes no .env'}, status=500)

    try:
        data = async_to_sync(_read_p110)(ip, tapo_user, tapo_pass)
        return Response({
            'dispositivo': DispositivoSerializer(disp).data,
            'ip': ip,
            **data
        })
    except Exception as e:
        return Response({'detail': f'Falha ao consultar P110: {e}'}, status=status.HTTP_502_BAD_GATEWAY)
    
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def dispositivos(request):
    user = request.user

    if request.method == 'GET':
        qs = Dispositivo.objects.filter(owner=user)
        return Response(DispositivoSerializer(qs, many=True).data)

    data = request.data or {}
    allowed = [
        'title', 'local', 'definicao', 'uso_energia', 'power',
        'tempo_exec', 'uso_ener', 'potencia_atual', 'ip'
    ]
    payload = {k: data.get(k) for k in allowed if k in data}

    disp = Dispositivo.objects.create(owner=user, **payload)
    return Response(DispositivoSerializer(disp).data, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def ingest_energy(request):
    server_secret = os.getenv("INGEST_SECRET")
    if not server_secret:
        return Response({"detail": "INGEST_SECRET não configurado no servidor."}, status=500)

    api_key = request.headers.get("X-Api-Key", "")
    if api_key != server_secret:
        return Response({"detail": "unauthorized"}, status=401)

    data = request.data or {}
    device_id = str(data.get("device_id") or "default")
    cache.set(f"energy:last:device:{device_id}", data, timeout=60)
    return Response({"ok": True})

@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def energy_latest_cached(request, device_id: int):
    snap = cache.get(f"energy:last:device:{device_id}")
    if not snap:
        return Response({"detail": "sem dados recentes para este device_id"}, status=status.HTTP_404_NOT_FOUND)
    return Response(snap, status=status.HTTP_200_OK)