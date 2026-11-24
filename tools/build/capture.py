import asyncio,sys,json,os,re
from playwright.async_api import async_playwright
JS=open('extract.js').read()
def slug(u):
    p=re.sub(r'^https://www\.ironhillslandscaping\.com','',u).strip('/')
    return p.replace('/','__') or 'index'
async def one(b,u,sem):
    async with sem:
        s=slug(u)
        if os.path.exists(f'pages/{s}.json') and '--force' not in sys.argv: return
        for attempt in range(3):
            ctx=await b.new_context(viewport={'width':1280,'height':900})
            pg=await ctx.new_page()
            try:
                await pg.goto(u,wait_until='load',timeout=90000)
                await pg.wait_for_timeout(2500)
                h=await pg.evaluate('document.documentElement.scrollHeight')
                y=0
                while y<h:
                    y+=500; await pg.evaluate(f'window.scrollTo(0,{y})'); await pg.wait_for_timeout(180)
                    h=await pg.evaluate('document.documentElement.scrollHeight')
                await pg.wait_for_timeout(2000)
                await pg.evaluate('window.scrollTo(0,0)'); await pg.wait_for_timeout(800)
                await pg.add_style_tag(content='*{content-visibility:visible !important}'); await pg.wait_for_timeout(1500)
                data=await pg.evaluate(JS)
                json.dump(data,open(f'pages/{s}.json','w'),indent=0)
                open(f'raw/{s}.html','w').write(await pg.content())
                await pg.screenshot(path=f'shots/{s}.png',full_page=True)
                print('ok',s,len(data['sections']),flush=True); await ctx.close(); return
            except Exception as e:
                print('ERR',s,attempt,str(e)[:300],flush=True)
            await ctx.close()
async def main():
    os.makedirs('pages',exist_ok=True);os.makedirs('raw',exist_ok=True);os.makedirs('shots',exist_ok=True)
    urls=[l.strip() for l in open(sys.argv[1]) if l.strip()]
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
        sem=asyncio.Semaphore(4)
        await asyncio.gather(*[one(b,u,sem) for u in urls])
        await b.close()
asyncio.run(main())
