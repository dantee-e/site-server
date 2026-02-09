import httpx
import os
from contextlib import asynccontextmanager
from httpx import AsyncClient
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTask


@asynccontextmanager
async def lifespan(app: FastAPI):
    global JELLYFIN
    print("printing")

    jellyfin_path = os.path.join(services_folder, "jellyfin")
    if os.path.isfile(jellyfin_path):
        print("Found jellyfin file ")
        with open(jellyfin_path, "r") as f:
            port = f.readline().strip()
            JELLYFIN = AsyncClient(base_url=f"http://localhost:{port}/")
    else:
        print("No jellyfin file found")

    yield


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

services_folder = os.path.join(os.curdir, "services")

# defaults
JELLYFIN = AsyncClient(base_url="http://localhost:8096/")


@app.get("/", response_class=HTMLResponse)
def main(request: Request):
    return templates.TemplateResponse("select_menu.html", {"request": request})


async def _reverse_proxy(
    request: Request, server: AsyncClient, path, prefix
) -> StreamingResponse:
    url = httpx.URL(path=path, query=request.url.query.encode("utf-8"))
    rp_req = server.build_request(
        request.method, url, headers=request.headers.raw, content=await request.body()
    )
    rp_resp = await server.send(rp_req, stream=True)
    headers = dict(rp_resp.headers)
    if "location" in headers:
        location = headers["location"]
        # If it's an absolute URL pointing to the backend
        if location.startswith(str(server.base_url)):
            # Replace backend URL with proxy URL
            location = location.replace(str(server.base_url).rstrip("/"), prefix)
            print(f"location is {location}")
            headers["location"] = location
        # If it's a relative URL, prepend the prefix
        else:  # location.startswith("/"):
            headers["location"] = f"{prefix}{location}"
            print(f"location is {location}")

    return StreamingResponse(
        rp_resp.aiter_raw(),
        status_code=rp_resp.status_code,
        headers=headers,
        background=BackgroundTask(rp_resp.aclose),
    )


# For each service, add an api_route like the one underneath  and call
#  the _reverse_proxy function passing as a parameter the path and the
#  AsyncClient that's connected to the service port
@app.api_route(
    "/jellyfin{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
)
async def proxy(request: Request, path: str):
    return await _reverse_proxy(request, JELLYFIN, path, "/jellyfin/")
