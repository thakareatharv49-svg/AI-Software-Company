from __future__ import annotations

from src.company.project_generator import GeneratedProject

def browser_calculator() -> GeneratedProject:
    return GeneratedProject(
        files={
            "index.html": """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Calculator</title><link rel="stylesheet" href="style.css"></head><body><main><p>AI SOFTWARE COMPANY</p><h1>Calculator</h1><div class="display"><small id="expression"></small><output id="display">0</output></div><div class="keys"><button data-action="clear">AC</button><button data-action="back">⌫</button><button data-op="%">%</button><button data-op="/">÷</button><button data-n="7">7</button><button data-n="8">8</button><button data-n="9">9</button><button data-op="*">×</button><button data-n="4">4</button><button data-n="5">5</button><button data-n="6">6</button><button data-op="-">−</button><button data-n="1">1</button><button data-n="2">2</button><button data-n="3">3</button><button data-op="+">+</button><button class="zero" data-n="0">0</button><button data-n=".">.</button><button class="eq" data-action="equals">=</button></div></main><script src="app.js"></script></body></html>""",
            "style.css": """*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:radial-gradient(circle at 20% 10%,#28386f,#0a0f22 45%,#05070d);font-family:system-ui,sans-serif;color:#fff}main{width:min(92vw,390px);padding:24px;border:1px solid #2b385d;border-radius:28px;background:#0b1120e8;box-shadow:0 30px 80px #0009}p{font-size:9px;letter-spacing:.2em;color:#8190b5}h1{margin:5px 0 18px}.display{height:115px;padding:16px;border:1px solid #263352;border-radius:18px;background:#060a14;text-align:right;display:flex;flex-direction:column;justify-content:end}.display small{height:22px;color:#7180a2}.display output{font-size:42px;font-weight:700;overflow:hidden}.keys{display:grid;grid-template-columns:repeat(4,1fr);gap:9px;margin-top:14px}.keys button{height:60px;border:1px solid #2a3758;border-radius:15px;background:#111a30;color:#fff;font-size:18px;font-weight:700;cursor:pointer}.keys button:hover{background:#1b2845}.keys button[data-op]{background:#202a50}.keys .eq{background:#655bd1}.keys .zero{grid-column:span 2}""",
            "app.js": """const d=document.querySelector("#display"),e=document.querySelector("#expression");let cur="0",prev=null,op=null,reset=false;function render(){d.textContent=cur;e.textContent=prev===null?"":prev+" "+op}function input(x){if(reset){cur=x==="."?"0.":x;reset=false}else if(x==="."&&cur.includes("."))return;else if(cur==="0"&&x!==".")cur=x;else cur+=x;render()}function calc(){if(prev===null||!op)return;let a=+prev,b=+cur,r=op==="+"?a+b:op==="-"?a-b:op==="*"?a*b:op==="/"?(b===0?"Error":a/b):a%b;cur=String(r);prev=null;op=null;reset=true;render()}function setop(x){if(cur==="Error")return;if(prev!==null)calc();prev=cur;op=x;reset=true;render()}document.querySelectorAll("[data-n]").forEach(b=>b.onclick=()=>input(b.dataset.n));document.querySelectorAll("[data-op]").forEach(b=>b.onclick=()=>setop(b.dataset.op));document.querySelector('[data-action="equals"]').onclick=calc;document.querySelector('[data-action="clear"]').onclick=()=>{cur="0";prev=null;op=null;reset=false;render()};document.querySelector('[data-action="back"]').onclick=()=>{if(!reset)cur=cur.length>1?cur.slice(0,-1):"0";render()};document.onkeydown=x=>{if(/[0-9.]/.test(x.key))input(x.key);else if("+-*/%".includes(x.key))setop(x.key);else if(x.key==="Enter"||x.key==="=")calc();else if(x.key==="Escape")document.querySelector('[data-action="clear"]').click()};render();""",
            "calculator.py": """def add(a, b):
    return a + b


def sub(a, b):
    return a - b


def mul(a, b):
    return a * b


def div(a, b):
    if b == 0:
        raise ZeroDivisionError("division by zero")
    return a / b
""",
            "tests/test_calculator.py": """from pathlib import Path

import calculator


def test_add():
    assert calculator.add(1, 2) == 3


def test_sub():
    assert calculator.sub(2, 1) == 1


def test_mul():
    assert calculator.mul(2, 3) == 6


def test_div():
    assert calculator.div(6, 3) == 2


def test_browser_files():
    root = Path(__file__).resolve().parents[1]
    assert all((root / name).is_file() for name in ("index.html", "style.css", "app.js"))
""",
        },
        test_command=["python","-m","pytest","-q"],
    )
