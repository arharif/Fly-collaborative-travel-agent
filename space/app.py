# ============================================================================
# CELL 16 — FLY | PINK TRAVEL STUDIO + CONVERSATIONAL CHAT (GRADIO 6.x)
# Standalone Hugging Face Gradio Space app.
# Adapted from the student's working Cell 16; imports agent_backend.py.
# ============================================================================
import copy
import os
from agent_backend import make_collaborative_travel_agent
import html
import re
import threading
import logging
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from urllib.parse import quote, urlparse

import gradio as gr
import requests

if int(gr.__version__.split(".")[0]) < 6:
    raise RuntimeError("This Cell 16 is for Gradio 6.x. Your version: " + gr.__version__)

# ---------- VISUAL DESIGN — pink, clean, responsive --------------------------
FLY_CSS = r"""
body,.gradio-container{background:#fff9fc!important;color:#191417!important;
 font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif!important}
.gradio-container{max-width:1440px!important;margin:0 auto!important}
.fly-top{background:#f9e3f0;border:1px solid #f1d6e3;border-radius:28px;
 padding:26px 30px;margin:5px 0 17px}
.fly-eyebrow{font-size:12px;letter-spacing:2px;font-weight:850;color:#3f2f3b}
.fly-top h1{margin:9px 0!important;font-size:clamp(32px,4vw,55px);
 letter-spacing:-1.8px;line-height:1.06;font-weight:850;color:#161216!important}
.fly-top p{font-size:15px;color:#756471;line-height:1.55;margin:0}
.fly-panel{background:white!important;border:1px solid #f0dfe8;border-radius:25px;
 padding:14px;box-shadow:0 8px 22px rgba(81,32,62,.035)}
.fly-kicker{font-size:12px;letter-spacing:1.8px;font-weight:850;color:#4a3340;
 padding:5px 0 10px}
.fly-summary{border-radius:25px;padding:22px;margin-bottom:7px;
 background:#f9e5f1;border:1px solid #f0d1e3;overflow:hidden}
.fly-summary small{font-weight:850;letter-spacing:2px;font-size:11px;color:#30212a}
.fly-summary h2{font-size:clamp(29px,3vw,49px);line-height:1.04;letter-spacing:-1.2px;
 margin:12px 0!important;color:#161116!important;word-break:break-word}
.fly-summary p{color:#65525d;font-size:14px;line-height:1.65;margin:11px 0 3px}
.fly-tag{display:inline-block;border-radius:100px;background:#fff;padding:7px 12px;
 font-size:11px;font-weight:750;margin:6px 6px 0 0;color:#2a2027}
.fly-cover{width:100%;height:218px;object-fit:cover;border-radius:20px;margin:8px 0;display:block}
.fly-cover-blank{height:120px;border-radius:20px;display:flex;align-items:center;
 justify-content:center;font-size:36px;background:linear-gradient(135deg,#eec6dd,#fbf0f6);color:#6d4056}
.fly-status{background:#fff1f8;border:1px solid #efd5e5;padding:13px 16px;
 border-radius:16px;color:#593b4a;font-size:13px;font-weight:650;margin-bottom:8px}
.fly-status.good{background:#f0f9f3;border-color:#d1e9da;color:#266741}
.fly-status.bad{background:#fff0f0;border-color:#f3caca;color:#9a3030}
.fly-spin{display:inline-block;vertical-align:middle;width:18px;height:18px;
 border:3px solid #efc8dd;border-top-color:#151015;border-radius:50%;
 animation:flyspin .9s linear infinite;margin-right:8px}
@keyframes flyspin{to{transform:rotate(360deg)}}
.fly-places{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}
.fly-place{border:1px solid #f0dce6;border-radius:19px;overflow:hidden;background:white}
.fly-place img{display:block;width:100%;height:128px;object-fit:cover}
.fly-place div{padding:11px}.fly-place b{font-size:13px;color:#241922;display:block}
.fly-place a{font-size:12px;font-weight:700;text-decoration:none;color:#9b3f72;
 display:inline-block;margin:7px 10px 0 0}
.fly-muted{font-size:12px;color:#82717e;margin-top:6px}
#fly-chatbot{border:1px solid #eed6e3!important;border-radius:20px!important}
#fly-generate,#fly-send{background:#151315!important;color:white!important;
 border-radius:15px!important;border:0!important;font-weight:800!important;min-height:49px!important}
#fly-send{min-width:106px!important}
#fly-chat-box textarea{border-radius:16px!important}
.fly-tip{font-size:12px;color:#816e79}
@media(max-width:780px){.fly-top{padding:21px}.fly-summary{padding:19px}
 .fly-top h1{font-size:34px}}
"""

# ---------- SESSION DATA -----------------------------------------------------
WELCOME = [{"role":"assistant","content":(
    "### ✈️ Hey, I'm Fly!\n"
    "Tell me what kind of trip you're dreaming of in the **Discovery Brief**. "
    "I'll create the first plan, and then you can ask me anything about it right here.")}]

def _new_state():
    return {"built": False, "snapshot": {}, "plan": "", "dialogue": []}

def _txt(v, fallback=""):
    v = "" if v is None else str(v).strip()
    return v if v else fallback

def _status(message, mode="normal", spinning=False):
    cls = "fly-status" + (" good" if mode == "good" else " bad" if mode == "bad" else "")
    marker = '<span class="fly-spin" aria-label="Planning"></span>' if spinning else ("✓ " if mode == "good" else "✦ ")
    return f'<div class="{cls}" role="status">{marker}{html.escape(message)}</div>'

def _maps_link(name, destination=""):
    return "https://www.google.com/maps/search/?api=1&query=" + quote((name+" "+destination).strip(), safe="")

def _trusted_https(url, domain):
    try:
        parsed = urlparse(url)
        return (parsed.scheme == "https" and bool(parsed.hostname) and
                (parsed.hostname == domain or parsed.hostname.endswith("."+domain)))
    except (ValueError, TypeError):
        return False

# Only real Wikimedia thumbnails are displayed. Never generate fake image URLs.
_LOG = logging.getLogger("fly.images")
_WIKI_HEADERS = {
    # Wikimedia requires an identifiable application with a contact URL.
    "User-Agent": "FlyTravelPlanner/1.2 (https://huggingface.co/spaces/melmir/haii-fly-travel-live)",
    "Accept": "application/json",
}


def _wikimedia_photo(url):
    """Validate the returned photo URL (including newer thumb.wikimedia.org)."""
    if not isinstance(url, str):
        return ""
    if url.startswith("//"):
        url = "https:" + url
    return url if _trusted_https(url, "wikimedia.org") else ""


def _wiki_tokens(value):
    """Normalize diacritics: Senso-ji and Sensō-ji should match."""
    plain = unicodedata.normalize("NFKD", str(value).casefold())
    plain = "".join(c for c in plain if not unicodedata.combining(c))
    return set(re.findall(r"[a-z0-9]+", plain)) - {
        "the", "of", "in", "at", "and", "japan", "france", "italy", "usa",
        "united", "states", "city", "prefecture", "district"
    }


def _wiki_is_match(asked, title):
    a, b = _wiki_tokens(asked), _wiki_tokens(title)
    if not a or not b:
        return False
    # Prefer a strong match, but accept a verified full-name subset.
    return len(a & b) / max(1, min(len(a), len(b))) >= 0.67


def _wiki_candidate_titles(query):
    query = str(query or "").strip()
    parts = [query]
    if "," in query:
        parts.append(query.split(",", 1)[0].strip())
    return list(dict.fromkeys(part for part in parts if part))


@lru_cache(maxsize=150)
def _wiki_media(query):
    """Return a confirmed Wikipedia place + real Wikimedia photograph.

    Uses REST page summary first (reliable for destinations / attractions),
    then REST page search and, if necessary, MediaWiki PageImages.
    Missing photographs are omitted instead of showing an unrelated image.
    """
    title_options = _wiki_candidate_titles(query)

    def from_summary(title):
        address = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(title.replace(" ", "_"), safe="")
        response = requests.get(address, headers=_WIKI_HEADERS, timeout=5)
        response.raise_for_status()
        data = response.json()
        page_title = data.get("title", "")
        page_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
        if not _wiki_is_match(query, page_title) and not _wiki_is_match(title, page_title):
            return None
        if not _trusted_https(page_url, "wikipedia.org"):
            return None
        photo = _wikimedia_photo((data.get("thumbnail") or {}).get("source"))
        if not photo:
            photo = _wikimedia_photo((data.get("originalimage") or {}).get("source"))
        return {"title": page_title, "page": page_url, "image": photo}

    # 1. Direct page summary; a city like "Kyoto, Japan" falls back to "Kyoto".
    for title in title_options:
        try:
            hit = from_summary(title)
            if hit and hit.get("image"):
                return hit
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            _LOG.info("Wikipedia summary lookup failed for %r: %s", title, type(exc).__name__)

    # 2. REST page search resolves alternate spellings and article redirects.
    try:
        response = requests.get(
            "https://en.wikipedia.org/w/rest.php/v1/search/page",
            params={"q": title_options[-1] if title_options else str(query), "limit": 5},
            headers=_WIKI_HEADERS, timeout=5,
        )
        response.raise_for_status()
        for page in response.json().get("pages", []):
            title = page.get("title", "")
            if not _wiki_is_match(query, title):
                continue
            # Upgrade small REST-search thumbnails to full page-summary size.
            try:
                detailed = from_summary(page.get("key") or title)
                if detailed and detailed.get("image"):
                    return detailed
            except (requests.RequestException, ValueError, KeyError, TypeError):
                pass
            thumb = _wikimedia_photo((page.get("thumbnail") or {}).get("url"))
            if thumb:
                article = "https://en.wikipedia.org/wiki/" + quote(
                    str(page.get("key") or title).replace(" ", "_"), safe="")
                return {"title": title, "page": article, "image": thumb}
    except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
        _LOG.info("Wikipedia REST search failed for %r: %s", query, type(exc).__name__)

    # 3. Original PageImages API, with accent-tolerant matching.
    try:
        response = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query", "format": "json", "formatversion": "2",
                "generator": "search", "gsrsearch": query, "gsrlimit": 5,
                "prop": "info|pageimages", "inprop": "url",
                "piprop": "thumbnail", "pithumbsize": 700, "pilicense": "free",
            },
            headers=_WIKI_HEADERS, timeout=5,
        )
        response.raise_for_status()
        for page in response.json().get("query", {}).get("pages", []):
            title = page.get("title", "")
            photo = _wikimedia_photo((page.get("thumbnail") or {}).get("source"))
            url = page.get("fullurl", "")
            if _wiki_is_match(query, title) and photo and _trusted_https(url, "wikipedia.org"):
                return {"title": title, "page": url, "image": photo}
    except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
        _LOG.warning("No Wikimedia image could be retrieved for %r (%s)", query, type(exc).__name__)

    return None

def _cover(s, media=None):
    dest = html.escape(_txt(s.get("destination"),"Your next escape"))
    duration = html.escape(_txt(s.get("duration"),"A journey to remember"))
    season = html.escape(_txt(s.get("season"),"Anytime"))
    interests = list(s.get("interests",[]) or [])[:3]
    tags = "".join(f'<span class="fly-tag">{html.escape(str(v))}</span>' for v in [duration,season]+interests)
    if media and media.get("image"):
        photo = f'<img class="fly-cover" loading="lazy" alt="Destination view" src="{html.escape(media["image"],quote=True)}">'
    else:
        photo = '<div class="fly-cover-blank" aria-hidden="true">✈</div>'
    return (f'<div class="fly-summary"><small>YOUR NEXT ESCAPE</small><h2>{dest.upper()}</h2>'
            f'{photo}<p>Thoughtful experiences, chosen around what matters to you.</p>{tags}</div>')

# ---------- TRIP-SETUP INPUTS ------------------------------------------------
def _resolve_duration(choice, custom):
    if choice != "Custom":
        return choice
    text = _txt(custom)
    m = re.fullmatch(r"\s*(\d{1,2})\s*(day|days|week|weeks|night|nights)?\s*",text,re.I)
    if not m:
        raise ValueError("Enter a duration such as '8 days' or '2 weeks'.")
    num = int(m.group(1))
    unit = (m.group(2) or "days").lower()
    days = num*7 if unit.startswith("week") else num
    if not (1 <= days <= 30):
        raise ValueError("Choose between 1 and 30 days for the itinerary.")
    return f"{days} days" + (f" ({text})" if unit.startswith("week") else "")

def _trip_snapshot(destination, duration, custom_duration, season, month, group, count,
                   interests, other_interests, stay, budget, notes):
    dest = _txt(destination)
    if not dest:
        raise ValueError("Enter a destination first, e.g., Tokyo, Japan.")
    resolved = _resolve_duration(duration, custom_duration)
    try:
        travelers = int(count)
        if travelers < 1 or travelers > 30 or float(count) != travelers:
            raise ValueError()
    except (ValueError,TypeError):
        raise ValueError("Number of travelers must be a whole number from 1 to 30.")
    selected = list(interests or [])
    typed = _txt(other_interests)
    if typed:
        selected.append("Other interests: " + typed[:450])
    return {
        "destination":dest[:160], "duration":resolved, "season":_txt(season,"Not sure"),
        "month":_txt(month), "group":_txt(group,"Just me"), "travelers":travelers,
        "interests":selected, "stay":_txt(stay,"No preference"),
        "budget":_txt(budget,"Flexible"), "notes":_txt(notes)[:1000]
    }

def _brief(s):
    return (f"Destination: {s['destination']}\nDuration: {s['duration']}\n"
            f"Season: {s['season']}\nMonth: {s['month'] or 'Not specified'}\n"
            f"Travel party: {s['group']} ({s['travelers']} traveler(s))\n"
            f"Interests: {', '.join(s['interests']) or 'Open to suggestions'}\n"
            f"Accommodation: {s['stay']}\nBudget: {s['budget']}\n"
            f"Other requirements: {s['notes'] or 'None'}")

# ---------- MODEL INVOCATION -------------------------------------------------
# Each request uses its own agent object. Explicit per-session state is passed
# in prompts. This avoids one visitor inheriting another visitor's memory.
_FLY_RUN_LOCK = threading.Lock()

def _run_fly(prompt):
    # Do not attempt a Bedrock request when deployment secrets are absent.
    if not (os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY")):
        raise RuntimeError("AWSSecretsMissing")
    with _FLY_RUN_LOCK:
        fresh_agent = make_collaborative_travel_agent()
        result = fresh_agent.run(prompt, reset=True)
    text = _txt(result)
    if not text or text.lower() == "none":
        raise RuntimeError("EmptyAgentAnswer")
    return text

def _safe_error(err):
    # Never expose raw AWS exceptions: they can contain private request details.
    if str(err) == "AWSSecretsMissing":
        return ("Fly is not yet connected to AWS Bedrock. The Space owner "
                "must configure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY "
                "under Space Settings → Secrets.")
    return ("Fly couldn't complete that request (" + type(err).__name__ + "). "
            "Your inputs are preserved. Please retry; if the issue persists, "
            "inspect Space logs privately; never share credentials.")

def _separate_places(raw):
    """Read the agent's optional places block or extract named attractions."""
    pattern = r"```places\s*\n([\s\S]*?)\n```"
    blocks = re.findall(pattern, raw, flags=re.I)
    clean = re.sub(pattern, "", raw, flags=re.I).strip()
    names = []
    for block in blocks:
        for line in block.splitlines():
            name = re.sub(r"^[-*\d.)\s]+", "", line).strip()[:90]
            if (3 <= len(name) <= 90 and not any(c in name for c in "<>[]{}") and
                    name.casefold() not in [n.casefold() for n in names]):
                names.append(name)
    # A language model may omit the optional fenced block: use named bold attractions.
    if not names:
        ignore = {
            "trip snapshot", "why this fits", "why it fits", "budget guidance",
            "stay recommendation", "your preferences", "optional refinements",
            "travel tips", "practical tips", "things to know",
        }
        for match in re.findall(r"\*\*([^*\n]{4,65})\*\*", clean):
            name = match.strip(" :-–—.!?,")
            if (name.casefold() not in ignore and not re.match(r"^(day|morning|evening|afternoon)\s*\d*\b", name, re.I)
                    and not re.match(r"^(\d|\$|\€)", name)
                    and not any(c in name for c in "<>[]{}")
                    and name.casefold() not in [n.casefold() for n in names]):
                names.append(name)
            if len(names) >= 3:
                break
    return clean, names[:3]

def _place_visuals(names, destination):
    # Images are optional and intentionally fetched AFTER the assistant's answer.
    # Always include the destination itself for at least one cover-photo lookup.
    # Follow with up to three distinct attractions (when the model supplied them).
    names = [destination] + [n for n in (names or []) if n.casefold() != destination.casefold()][:3]
    with ThreadPoolExecutor(max_workers=min(3,len(names))) as executor:
        media = list(executor.map(_wiki_media, names))
    lines = ["\n---\n**Explore the places**"]
    cards = []
    for name, found in zip(names,media):
        article = found.get("page","") if found else ""
        image = found.get("image","") if found else ""
        title = found.get("title",name) if found else name
        maps = _maps_link(name,destination if name.casefold()!=destination.casefold() else "")
        safe_title = html.escape(title)
        safe_maps = html.escape(maps,quote=True)
        image_html = f'<img loading="lazy" src="{html.escape(image,quote=True)}" alt="{safe_title}">' if image else ""
        wiki_html = (f'<a href="{html.escape(article,quote=True)}" target="_blank" rel="noopener noreferrer">Details ↗</a>'
                     if article else "")
        cards.append(f'<div class="fly-place">{image_html}<div><b>{safe_title}</b>{wiki_html}'
                     f'<a href="{safe_maps}" target="_blank" rel="noopener noreferrer">Maps ↗</a></div></div>')
        # Use actual returned photo URL only; never construct fake image URLs.
        md_title = re.sub(r"[\[\]()\\]","",title)
        if image:
            lines.append(f"![{md_title}]({image})")
        lines.append(f"**{md_title}** · " +
                     (f"[Read more]({article}) · " if article else "") +
                     f"[Locate on Google Maps]({maps})")
    lines.append("*Photos: Wikimedia/Wikipedia; click article links for source information and attribution. "
                 "Map links are searches, not confirmed opening hours, prices, or availability.*")
    return "\n\n".join(lines), '<div class="fly-places">'+"".join(cards)+"</div>"

# ---------- CALLBACKS --------------------------------------------------------
def build_trip(destination,duration,custom_duration,season,month,group,count,
               interests,other_interests,stay,budget,notes,history,state):
    history = copy.deepcopy(history or WELCOME)
    state = copy.deepcopy(state or _new_state())
    try:
        s = _trip_snapshot(destination,duration,custom_duration,season,month,group,count,
                           interests,other_interests,stay,budget,notes)
    except (ValueError,TypeError) as e:
        yield history,_status(str(e),"bad"),_cover(state.get("snapshot",{})),"",state
        return
    history = [{"role":"user","content":"**My travel brief**\n\n"+_brief(s).replace("\n","  \n")},
               {"role":"assistant","content":"✈️ **Fly is designing your journey...**"}]
    yield history,_status("Putting your journey together...","normal",True),_cover(s),"",state
    prompt = ("MODE A — BUILD ITINERARY. Here is the traveler's confirmed brief:\n"+_brief(s)+
       "\nCreate a practical day-by-day itinerary with brief reasons for recommendations. "
       "Do not ask more setup questions. Ensure every named destination is relevant. "
       "Avoid unsupported prices/hours/booking assertions. Return Markdown and a small places block.")
    try:
        text = _run_fly(prompt)
        plan, places = _separate_places(text)
        if not plan:
            raise RuntimeError("EmptyItinerary")
    except Exception as exc:
        history[-1]["content"] = _safe_error(exc)
        yield history,_status("Generation failed — your travel brief is still on screen.","bad"),_cover(s),"",state
        return
    state = {"built":True,"snapshot":s,"plan":plan,"dialogue":[]}
    history[-1]["content"] = plan
    yield history,_status("Itinerary ready. Adding optional place photos and links...","normal",True),_cover(s),"",state
    try:
        appendix, cards = _place_visuals(places,s["destination"])
        photo = _wiki_media(s["destination"])
    except Exception:
        appendix = "\n\n[Explore this destination on Maps]("+_maps_link(s["destination"])+")"
        cards = '<div class="fly-muted">Place photographs are temporarily unavailable.</div>'
        photo = None
    history[-1]["content"] = plan+"\n\n"+appendix
    images_loaded = cards.count('<img ') + int(bool(photo and photo.get("image")))
    if images_loaded:
        final_status = _status("Your itinerary and place photographs are ready. Ask Fly anything!", "good")
    else:
        final_status = _status("Your itinerary is ready. Wikimedia photos were unavailable; place links still work.")
    yield history,final_status,_cover(s,photo),cards,state

def chat_send(message,history,state):
    history = copy.deepcopy(history or WELCOME)
    state = copy.deepcopy(state or _new_state())
    question = _txt(message)
    if not question:
        yield history,_status("Type a message before pressing Send.","bad"),state,message
        return
    if len(question)>2500:
        yield history,_status("Please shorten your message to 2,500 characters.","bad"),state,message
        return
    history.append({"role":"user","content":question})
    history.append({"role":"assistant","content":"<span class='fly-spin'></span> Fly is thinking..."})
    yield history,_status("Fly is preparing an answer...","normal",True),state,""
    brief = _brief(state["snapshot"]) if state.get("built") else "No full travel brief has been submitted yet."
    plan = state.get("plan","")[:6800]
    dialogue = state.get("dialogue",[])[-6:]
    context = "\n".join(("Traveler: " if x["role"]=="user" else "Fly: ")+x["content"][:1000]
                        for x in dialogue)
    prompt = ("MODE B — CONVERSATION. Answer the traveler's LATEST question. "
              "Do not repeat or regenerate the full itinerary unless explicitly asked. "
              "A brief, relevant answer is best. Honor recent corrections.\n\n"
              "TRAVEL BRIEF:\n"+brief+"\n\nSAVED ITINERARY (reference only):\n"+
              (plan or "No itinerary yet")+"\n\nRECENT CONVERSATION:\n"+
              (context or "No earlier chat")+"\n\nLATEST USER QUESTION:\n"+question)
    try:
        answer_raw = _run_fly(prompt)
        answer, names = _separate_places(answer_raw)
        if not answer:
            raise RuntimeError("EmptyChatAnswer")
    except Exception as exc:
        history[-1]["content"] = _safe_error(exc)
        yield history,_status("Answer failed — you can retry your question.","bad"),state,question
        return
    # Keep only successful Q/A turns in the session's dialogue context.
    state.setdefault("dialogue",[]).extend([{"role":"user","content":question},
                                             {"role":"assistant","content":answer}])
    state["dialogue"] = state["dialogue"][-12:]
    history[-1]["content"] = answer
    yield history,_status("Ready for your next question.","good"),state,""
    if names:
        try:
            links,_cards = _place_visuals(names,state.get("snapshot",{}).get("destination",""))
            history[-1]["content"] = answer+"\n\n"+links
            yield history,_status("Ready for your next question.","good"),state,""
        except Exception:
            pass

def example_tokyo():
    return "Tokyo, Japan","7 days","","Spring","April","Family",4,\
           ["Food & local cuisine","Culture & history","Nature & scenic places"],\
           "Quiet gardens, local markets","Ryokan","Balanced mid-range",\
           "Family-friendly, relaxed pace and a mix of traditional and modern Tokyo."

def example_kyoto():
    return "Kyoto, Japan","Custom","8 days","Spring","April","My partner",2,\
           ["Culture & history","Hidden gems"],"Tea ceremonies and peaceful walks",\
           "Ryokan","Balanced mid-range","Avoid peak crowds when possible."

def example_paris():
    return "Paris, France","5 days","","Fall","October","Friends",3,\
           ["Food & local cuisine","Art & museums"],"Photography and independent bookstores",\
           "Hotel","Balanced mid-range","Walkable neighborhoods and good cafés."

def preview():
    """Offline model demo, with live Wikimedia image check (no AWS cost)."""
    s={"destination":"Tokyo, Japan","duration":"7 days","season":"Spring",
       "interests":["Culture & history","Nature & scenic places"]}
    sample = (
        "## Tokyo · Sample itinerary (preview only)\n"
        "### Day 1 — Asakusa\nVisit **Sensō-ji** and explore the historic streets nearby.\n\n"
        "### Day 2 — A slower day\nExplore **Shinjuku Gyoen**, subject to current access details.\n\n"
        "**Why these places?** They combine cultural heritage and green spaces.\n\n"
        "*This is a preview. No AWS/DeepSeek request was made.*"
    )
    chat=[{"role":"assistant","content": sample}]
    try:
        appendix, cards = _place_visuals(["Sensō-ji", "Shinjuku Gyoen"], "Tokyo, Japan")
        image = _wiki_media("Tokyo, Japan")
        chat[0]["content"] += "\n\n" + appendix
        count = cards.count('<img ') + int(bool(image and image.get('image')))
        note = (f"Preview ready: {count} verified Wikimedia image(s) found (no AWS request)."
                if count else "Preview ready, but the Space could not retrieve Wikimedia photos. See Logs for lookup errors.")
        return chat,_status(note,"good" if count else "normal"),_cover(s,image),cards,_new_state()
    except Exception as exc:
        _LOG.warning("Image preview failed: %s", type(exc).__name__)
        return chat,_status("Preview ready. Image service unavailable from the Space."),_cover(s),"",_new_state()

def reset():
    inputs=("","7 days",gr.update(value="",visible=False),"Not sure","","Just me",1,
            [],"","No preference","Balanced mid-range","")
    outputs=(copy.deepcopy(WELCOME),_status("Ready for your next journey."),_cover({}),"",_new_state(),"")
    return inputs+outputs

def show_custom(choice):
    return gr.update(visible=choice=="Custom")

# ---------- ACTUAL GRADIO UI -------------------------------------------------
with gr.Blocks(title="Fly | Your Travel Buddy",fill_height=True) as fly_demo:
    state=gr.State(_new_state())
    gr.HTML('''<div class="fly-top"><div class="fly-eyebrow">✈ FLY / YOUR TRAVEL BUDDY</div>
      <h1>Some journeys are designed around you.</h1>
      <p>A thoughtful travel brief, your own itinerary, and a personal concierge that stays in the conversation.</p></div>''')
    with gr.Row(equal_height=False):
        with gr.Column(scale=5,min_width=310,elem_classes=["fly-panel"]):
            gr.HTML('<div class="fly-kicker">01 / YOUR DISCOVERY BRIEF</div>')
            cover=gr.HTML(_cover({}))
            destination=gr.Textbox(label="Destination",placeholder="e.g., Tokyo, Japan")
            with gr.Row():
                duration=gr.Dropdown(["3 days","4 days","5 days","7 days","10 days","14 days","Custom"],
                        value="7 days",label="Duration")
                season=gr.Dropdown(["Spring","Summer","Fall","Winter","Not sure"],
                        value="Not sure",label="When?")
            custom_duration=gr.Textbox(label="Your duration (custom)",
                        placeholder="e.g., 8 days or 2 weeks",visible=False)
            month=gr.Textbox(label="Month (optional)",placeholder="e.g., April")
            with gr.Row():
                group=gr.Dropdown(["Just me","My partner","Friends","Family"],
                        value="Just me",label="Who is traveling?")
                count=gr.Number(value=1,precision=0,minimum=1,maximum=30,label="Travelers")
            interests=gr.CheckboxGroup(
                ["Food & local cuisine","Culture & history","Nature & scenic places",
                 "Shopping","Anime & gaming","Nightlife","Art & museums","Hidden gems","Adventure"],
                label="What do you love? (select any)",value=[])
            other_interests=gr.Textbox(label="Other interests (optional)",
                placeholder="e.g., architecture, vintage shopping, street photography, jazz…")
            with gr.Row():
                stay=gr.Dropdown(["Hotel","Airbnb","Ryokan","No preference"],
                        value="No preference",label="Where would you stay?")
                budget=gr.Dropdown(["Smart budget","Balanced mid-range","Premium comfort","Luxury"],
                        value="Balanced mid-range",label="Budget style")
            notes=gr.Textbox(lines=3,label="Anything else? (optional)",
                placeholder="Daily budget, mobility needs, dietary preferences, places to avoid, pace…")
            gr.Markdown("**Start with an example**")
            with gr.Row():
                tokyo=gr.Button("🌸 Tokyo",size="sm")
                kyoto=gr.Button("⛩️ Kyoto",size="sm")
                paris=gr.Button("🥐 Paris",size="sm")
            generate=gr.Button("✦ Design my journey →",variant="primary",elem_id="fly-generate")
            with gr.Row():
                preview_btn=gr.Button("Preview (no AWS)",size="sm")
                reset_btn=gr.Button("Start over",size="sm")
            gr.HTML('<div class="fly-tip">Your free-text answers are used together with any selected options.</div>')
        with gr.Column(scale=6,min_width=315):
            gr.HTML('<div class="fly-kicker">02 / YOUR PERSONAL CONCIERGE</div>')
            status=gr.HTML(_status("Ready — tell Fly about your next journey."))
            chatbot=gr.Chatbot(value=copy.deepcopy(WELCOME),height=610,label="Fly",elem_id="fly-chatbot")
            with gr.Row(equal_height=False):
                chat_input=gr.Textbox(label="Your message",show_label=False,lines=2,
                    placeholder="Ask Fly anything about your trip…",scale=8,elem_id="fly-chat-box")
                send=gr.Button("Send ↗",variant="primary",scale=1,elem_id="fly-send")
            gr.HTML('<div class="fly-tip">Ask about a place, transport, the budget, or a change to one day. Fly will answer without rebuilding the entire trip.</div>')
            gr.HTML('<div class="fly-kicker" style="margin-top:14px">PLACES FROM YOUR ITINERARY</div>')
            gallery=gr.HTML('<div class="fly-muted">Photos and place links appear after planning when available.</div>')

    inputs=[destination,duration,custom_duration,season,month,group,count,
            interests,other_interests,stay,budget,notes]
    outputs=[chatbot,status,cover,gallery,state]
    duration.change(show_custom,inputs=duration,outputs=custom_duration,queue=False)
    for btn,fn in [(tokyo,example_tokyo),(kyoto,example_kyoto),(paris,example_paris)]:
        btn.click(fn=fn,outputs=inputs,queue=False)
    generate.click(build_trip,inputs=inputs+[chatbot,state],outputs=outputs,show_progress="minimal")
    send.click(chat_send,inputs=[chat_input,chatbot,state],outputs=[chatbot,status,state,chat_input],show_progress="minimal")
    chat_input.submit(chat_send,inputs=[chat_input,chatbot,state],outputs=[chatbot,status,state,chat_input],show_progress="minimal")
    preview_btn.click(preview,outputs=outputs,queue=False)
    reset_btn.click(reset,outputs=inputs+outputs+[chat_input],queue=False)

# In Gradio 6, theme and CSS belong to .launch(), NOT gr.Blocks().
# .queue() lets the user see the animated planning state before the AI finishes.
fly_demo.queue(default_concurrency_limit=1)
if __name__ == "__main__":
    # A Space already serves HTTPS; never create a Gradio share tunnel here.
    # Set FLY_APP_USER and FLY_APP_PASSWORD as Space Secrets for access control.
    password = os.getenv("FLY_APP_PASSWORD", "").strip()
    auth = (os.getenv("FLY_APP_USER", "traveler"), password) if password else None
    fly_demo.launch(
        share=False, debug=False, show_error=False,
        server_name="0.0.0.0", server_port=7860,
        auth=auth,
        theme=gr.themes.Soft(), css=FLY_CSS,
    )
