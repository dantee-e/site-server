from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def main(request: Request):
    return templates.TemplateResponse("select_menu.html", {"request": request})


@app.api_route("/jellyfin")
async def proxy(_: Request):
    # Target server on another port
    target_url = "http://localhost:8096"

    return RedirectResponse(target_url)
