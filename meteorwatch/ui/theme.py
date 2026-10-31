"""The page stylesheet.

Three layers, in order:
  1. tokens        colours, fonts, page gutter
  2. components    status key, record sheet, callouts, and Streamlit widget overrides
  3. story         full-bleed hero, scroll-revealed chapters, counters, pinned section

Scroll-driven effects use ``animation-timeline: view()``. Chrome, Edge and Safari 26 run
them. Browsers without support (Firefox, at the time of writing) ignore them and show
the same content without the motion. Every animation is also switched off for people who
ask their system for reduced motion.
"""
from __future__ import annotations

from meteorwatch.ui.design import (
    BODY_FONT_CSS,
    DECK,
    DECK_2,
    DIM,
    DISPLAY_FONT_CSS,
    FAINT,
    LINE,
    SKY,
    TEXT,
)

_FONTS = (
    "@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400..800"
    "&family=Instrument+Sans:wght@400..700&display=swap');\n"
)

_TOKENS = f""":root{{
  --mw-sky:{SKY}; --mw-deck:{DECK}; --mw-deck2:{DECK_2}; --mw-line:{LINE};
  --mw-text:{TEXT}; --mw-dim:{DIM}; --mw-faint:{FAINT};
  --mw-display:{DISPLAY_FONT_CSS}; --mw-body:{BODY_FONT_CSS};
  --mw-gutter:clamp(1rem,5vw,4.5rem);
}}
"""

_COMPONENTS = """
/* ---- page ---- */
.stApp{background:var(--mw-sky);color:var(--mw-text);font-family:var(--mw-body);}
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button{font-family:var(--mw-body);}
[data-testid="stHeader"]{background:transparent;}
.block-container,[data-testid="stMainBlockContainer"]{max-width:1500px!important;padding:0 var(--mw-gutter) 4rem!important;}
[data-testid="stMain"],section.main{overflow-x:hidden;}
:focus-visible{outline:2px solid var(--mw-text)!important;outline-offset:2px;}
[data-testid="stElementContainer"]:has(> [data-testid="stMarkdownContainer"] > style),
.element-container:has(> .stMarkdown > style){display:none;}
a{color:var(--mw-text);text-underline-offset:3px;}

/* ---- status key ---- */
.mw-key{display:grid;grid-template-columns:minmax(180px,.8fr) 4fr;gap:1rem 2rem;align-items:start;margin:0 0 .9rem;}
@media (max-width:900px){.mw-key{grid-template-columns:1fr;}}
.mw-num{font-family:var(--mw-display);font-weight:700;font-variant-numeric:tabular-nums;letter-spacing:-.02em;color:var(--mw-text);line-height:1;}
.mw-key-total .mw-num{display:block;font-size:2.9rem;}
.mw-key-total .mw-cap{display:block;margin-top:.35rem;font-size:.86rem;color:var(--mw-dim);}
.mw-key ul.mw-key-list{list-style:none!important;margin:0!important;padding:0!important;display:grid;
  grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1rem 1.3rem;}
.mw-key-list li{display:grid;grid-template-columns:auto 1fr;column-gap:.55rem;align-items:center;margin:0!important;padding:0!important;}
.mw-key-list li .mw-num{font-size:1.7rem;}
.mw-key-list li .mw-cap{grid-column:2;font-size:.8rem;line-height:1.3;color:var(--mw-dim);}
.mw-key-list li.mw-zero{opacity:.5;}
.mw-dot{display:inline-block;width:.8rem;height:.8rem;border-radius:50%;flex:none;border:2px solid transparent;box-sizing:border-box;}
.mw-dot--hollow{background:transparent;}

/* ---- coverage bar ---- */
.mw-cover{margin:0 0 1.1rem;}
.mw-cover-bar{display:flex;height:10px;border-radius:999px;overflow:hidden;background:var(--mw-deck);border:1px solid var(--mw-line);}
.mw-cover-bar span{display:block;height:100%;}
.mw-cover-bar .a{background:var(--mw-text);}
.mw-cover-bar .n{background:repeating-linear-gradient(135deg,#7C86B8 0 4px,transparent 4px 8px);}
.mw-cover-bar .u{background:repeating-linear-gradient(135deg,#7C86B3 0 2px,transparent 2px 6px);}
.mw-cover p{font-size:.88rem;line-height:1.5;color:var(--mw-dim);margin:.5rem 0 0;max-width:84ch;}
.mw-cover p strong{color:var(--mw-text);}

/* ---- sections, callouts, empty states ---- */
.mw-section{margin:1.5rem 0 .6rem;}
.mw-section .mw-h2{font-family:var(--mw-display)!important;font-size:1.5rem!important;font-weight:650!important;
  letter-spacing:-.018em!important;line-height:1.2!important;margin:0!important;padding:0!important;color:var(--mw-text);}
.mw-section p{margin:.35rem 0 0;color:var(--mw-dim);max-width:70ch;line-height:1.55;font-size:.97rem;}
.mw-callout{border:1px solid var(--mw-line);border-left:4px solid var(--mw-text);border-radius:4px 12px 12px 4px;
  background:var(--mw-deck);padding:.85rem 1.05rem;margin:.6rem 0 1rem;font-size:.94rem;line-height:1.55;color:var(--mw-dim);max-width:92ch;}
.mw-callout strong{color:var(--mw-text);}
.mw-empty{border:1px dashed var(--mw-line);border-radius:12px;padding:2.2rem 1.4rem;text-align:center;margin:1rem 0;}
.mw-empty .mw-empty-title{font-family:var(--mw-display);font-size:1.25rem;font-weight:650;margin:0 0 .4rem;padding:0;color:var(--mw-text);}
.mw-empty p{margin:0;color:var(--mw-dim);}
.mw-legend-list{list-style:none!important;margin:.4rem 0 0!important;padding:0!important;}
.mw-legend-list li{display:grid;grid-template-columns:auto 1fr;gap:.2rem .7rem;align-items:start;margin:0 0 .85rem!important;padding:0!important;
  color:var(--mw-dim);font-size:.93rem;line-height:1.5;}
.mw-legend-list li strong{color:var(--mw-text);}
.mw-legend-list .mw-dot{margin-top:.28rem;}

/* ---- record sheet ---- */
.mw-sheet{background:var(--mw-deck);border:1px solid var(--mw-line);border-radius:16px;padding:1.4rem 1.5rem 1.2rem;}
.mw-sheet-head{display:flex;flex-wrap:wrap;align-items:center;gap:.5rem 1.1rem;margin-bottom:1.1rem;}
.mw-sheet-date{font-family:var(--mw-display);font-weight:750;font-size:clamp(1.5rem,3vw,2.1rem);letter-spacing:-.025em;line-height:1.1;margin:0;color:var(--mw-text);}
.mw-sheet-time{color:var(--mw-dim);margin:0;font-variant-numeric:tabular-nums;}
.mw-chip{display:inline-flex;align-items:center;gap:.55rem;border:1.5px solid var(--mw-line);border-radius:999px;padding:.22rem .8rem .22rem .6rem;
  font-size:.87rem;font-weight:600;color:var(--mw-text);}
.mw-chip.mw-chip--hollow{border-style:dashed;}
.mw-sheet-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:1.3rem 2.4rem;}
.mw-sheet .mw-h3{font-family:var(--mw-display)!important;font-size:1.02rem!important;font-weight:650!important;
  margin:0 0 .3rem!important;padding:0!important;color:var(--mw-dim);}
.mw-rows{margin:0;padding:0;display:grid;grid-template-columns:minmax(0,1fr) auto;column-gap:1.2rem;}
.mw-rows dt,.mw-rows dd{margin:0;padding:.55rem 0;border-bottom:1px solid rgba(51,64,122,.65);}
.mw-rows dt{color:var(--mw-dim);font-size:.9rem;}
.mw-rows dd{text-align:right;font-weight:600;font-variant-numeric:tabular-nums;color:var(--mw-text);}
.mw-rows dd .mw-dot{width:.62rem;height:.62rem;margin-right:.45rem;vertical-align:baseline;}
.mw-unit{color:var(--mw-faint);font-weight:400;margin-left:.35rem;font-size:.82rem;}
.mw-na{color:var(--mw-faint);font-weight:400;}
.mw-sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;}
.mw-sheet-note{color:var(--mw-dim);font-size:.85rem;line-height:1.5;margin:1rem 0 0;max-width:80ch;}

/* ---- sidebar ---- */
[data-testid="stSidebar"]{background:var(--mw-deck);border-right:1px solid var(--mw-line);}
.mw-side-title{font-family:var(--mw-display);font-weight:650;font-size:1.1rem;margin:.2rem 0 .4rem;color:var(--mw-text);}
.mw-inview{display:flex;align-items:baseline;gap:.55rem;margin:.1rem 0 .8rem;color:var(--mw-dim);font-size:.88rem;}
.mw-inview .mw-num{font-size:1.9rem;}

/* ---- Streamlit widgets ---- */
.stTabs [data-baseweb="tab-list"]{gap:.2rem;border-bottom:1px solid var(--mw-line);}
.stTabs button[data-baseweb="tab"]{font-family:var(--mw-display);font-weight:600;font-size:1.02rem;color:var(--mw-dim);
  padding:.7rem 1rem;background:transparent;}
.stTabs button[data-baseweb="tab"]:hover{color:var(--mw-text);background:transparent;}
.stTabs button[data-baseweb="tab"][aria-selected="true"]{color:var(--mw-text);}
.stTabs [data-baseweb="tab-highlight"]{background:var(--mw-text);height:3px;border-radius:3px;}
.stTabs [data-baseweb="tab-border"]{background:transparent;}
.stTabs .stTabs [data-baseweb="tab-list"]{border-bottom:none;gap:.4rem;margin-top:.4rem;}
.stTabs .stTabs button[data-baseweb="tab"]{font-size:.92rem;padding:.35rem .9rem;border:1px solid var(--mw-line);border-radius:999px;}
.stTabs .stTabs button[data-baseweb="tab"][aria-selected="true"]{background:var(--mw-deck2);border-color:var(--mw-dim);}
.stTabs .stTabs [data-baseweb="tab-highlight"]{display:none;}

[data-testid="stMetric"]{background:var(--mw-deck);border:1px solid var(--mw-line);border-radius:6px;padding:.85rem 1rem;}
[data-testid="stMetricLabel"] p{color:var(--mw-dim);font-size:.84rem;}
[data-testid="stMetricValue"]{font-family:var(--mw-display);font-weight:700;letter-spacing:-.02em;}

.stButton>button,.stDownloadButton>button,[data-testid="stBaseButton-secondary"]{border-radius:8px;border:1px solid var(--mw-line);
  background:transparent;color:var(--mw-text);font-weight:600;}
.stButton>button:hover,.stDownloadButton>button:hover,[data-testid="stBaseButton-secondary"]:hover{border-color:var(--mw-text);background:var(--mw-deck2);color:var(--mw-text);}
.stButton>button[kind="primary"],[data-testid="stBaseButton-primary"]{background:var(--mw-text);color:var(--mw-sky);border:1px solid var(--mw-text);}
.stButton>button[kind="primary"]:hover,[data-testid="stBaseButton-primary"]:hover{background:#FFFFFF;color:var(--mw-sky);}

[data-testid="stExpander"] details{border:1px solid var(--mw-line);border-radius:10px;background:transparent;}
[data-testid="stExpander"] summary{font-weight:600;}
[data-testid="stDataFrame"]{border:1px solid var(--mw-line);border-radius:8px;overflow:hidden;}
[data-testid="stCaptionContainer"]{color:var(--mw-dim);}
hr{border-color:var(--mw-line);}
"""

_STORY = """
/* =====================================================================
   Scroll story
   ===================================================================== */

/* ---- hero ---- */
.mw-hero{position:relative;isolation:isolate;overflow:hidden;min-height:100vh;display:flex;align-items:center;
  margin:0 calc(-1 * var(--mw-gutter));}
.mw-sky-wrap{position:absolute;inset:0;z-index:0;pointer-events:none;}
.mw-sky{position:absolute;inset:0;}
.mw-sky i{position:absolute;display:block;border-radius:50%;}
.mw-sky i.s1{width:2px;height:2px;} .mw-sky i.s2{width:3px;height:3px;}
.mw-sky i.s3{width:4px;height:4px;} .mw-sky i.s4{width:6px;height:6px;}
.mw-sky i.k-both{background:#FFD97A;box-shadow:0 0 10px 2px rgba(255,217,122,.55);}
.mw-sky i.k-base{background:#FF7B54;box-shadow:0 0 9px 2px rgba(255,123,84,.5);}
.mw-sky i.k-forest{background:#C79BFF;box-shadow:0 0 9px 2px rgba(199,155,255,.5);}
.mw-sky i.k-baseun{background:rgba(255,123,84,.5);}
.mw-sky i.k-quiet{background:rgba(95,169,184,.85);}
.mw-sky i.k-unass{background:rgba(124,134,184,.42);}
.mw-sky i.k-unk{background:rgba(138,143,168,.35);}
.mw-meteors{position:absolute;inset:0;z-index:1;pointer-events:none;overflow:hidden;}
.mw-meteors span{position:absolute;top:-16vh;width:2px;height:15vh;opacity:0;
  background:linear-gradient(180deg,transparent,rgba(236,234,246,.95));}
.mw-meteors span:nth-child(1){left:88%;} .mw-meteors span:nth-child(2){left:71%;}
.mw-meteors span:nth-child(3){left:96%;} .mw-meteors span:nth-child(4){left:58%;}
.mw-meteors span:nth-child(5){left:80%;} .mw-meteors span:nth-child(6){left:66%;}
.mw-hero-inner{position:relative;z-index:2;width:100%;box-sizing:border-box;padding:7rem var(--mw-gutter) 5.5rem;}
.mw-kicker{font-family:var(--mw-display);font-size:1rem;font-weight:600;color:var(--mw-dim);margin:0 0 1.2rem;letter-spacing:.01em;}
.mw-hero-title{font-family:var(--mw-display);font-weight:800;line-height:.9;letter-spacing:-.045em;margin:0 0 1.6rem;
  font-size:clamp(3.4rem,13.5vw,12rem);color:var(--mw-text);}
.mw-hero-title span{display:block;}
.mw-hero-lede{font-size:clamp(1.05rem,1.6vw,1.35rem);line-height:1.55;max-width:46ch;color:var(--mw-text);margin:0 0 .9rem;}
.mw-hero-key{font-size:.9rem;line-height:1.55;max-width:62ch;color:var(--mw-dim);margin:0 0 2.4rem;}
.mw-hero-stats{display:flex;flex-wrap:wrap;gap:1.4rem 3.4rem;margin:0 0 2.6rem;padding:0;}
.mw-hero-stats div{margin:0;}
.mw-hero-stats dt{order:2;color:var(--mw-dim);font-size:.9rem;margin:.4rem 0 0;}
.mw-hero-stats dd{order:1;margin:0;font-family:var(--mw-display);font-weight:750;font-size:clamp(2.4rem,5vw,4.2rem);
  letter-spacing:-.035em;line-height:1;font-variant-numeric:tabular-nums;color:var(--mw-text);}
.mw-hero-stats div{display:flex;flex-direction:column;}
.mw-scrollcue{display:inline-flex;flex-direction:column;align-items:flex-start;gap:.6rem;font-size:.85rem;color:var(--mw-dim);margin:0;}
.mw-scrollcue span{display:block;width:1px;height:3.4rem;background:linear-gradient(var(--mw-text),transparent);}

/* outlined type, only where the browser can stroke text */
.mw-out{color:var(--mw-text);}
@supports (-webkit-text-stroke:1px #fff){
  .mw-out{color:transparent;-webkit-text-stroke:2px var(--mw-text);}
}

/* ---- counters ---- */
@property --mw-n{syntax:"<integer>";inherits:false;initial-value:0;}
.mw-count{counter-reset:mwn var(--mw-n);}
.mw-count::after{content:counter(mwn);}

/* ---- statement: words light up as they scroll in ---- */
.mw-statement{max-width:1120px;margin:clamp(5rem,18vh,11rem) 0;}
.mw-statement p{font-family:var(--mw-display);font-weight:650;font-size:clamp(1.7rem,4.3vw,3.7rem);line-height:1.16;
  letter-spacing:-.028em;color:var(--mw-text);margin:0;}
.mw-statement .mw-kicker{margin-bottom:1.6rem;font-size:1rem;}

/* ---- chapter heads ---- */
.mw-chapter-head{padding-top:clamp(3.5rem,10vh,7rem);margin:0 0 1.6rem;}
.mw-chapter-no{font-family:var(--mw-display);font-weight:600;color:var(--mw-faint);font-size:1rem;margin:0 0 .8rem;}
.mw-chapter-title{font-family:var(--mw-display);font-weight:800;line-height:1;letter-spacing:-.04em;
  font-size:clamp(2.3rem,6.4vw,5.6rem);max-width:14ch;color:var(--mw-text);margin:0 0 1.2rem;}
.mw-chapter-title span{display:block;}
.mw-chapter-intro{font-size:1.08rem;line-height:1.6;max-width:56ch;color:var(--mw-dim);margin:0;}
.mw-chapter-intro strong{color:var(--mw-text);}

/* chapters built from Streamlit elements */
[class*="st-key-mw_"]{margin-bottom:clamp(2.5rem,8vh,6rem);}

/* ---- pinned scene ---- */
.mw-pin{display:grid;grid-template-columns:minmax(0,.9fr) minmax(0,1.1fr);gap:clamp(1.5rem,5vw,5rem);margin:clamp(3.5rem,10vh,7rem) 0;}
.mw-pin-left{position:sticky;top:18vh;align-self:start;}
.mw-pin-left .mw-chapter-title{max-width:11ch;}
.mw-step{border-top:1px solid var(--mw-line);padding:1.6rem 0 3.4rem;min-height:34vh;}
.mw-step-no{font-family:var(--mw-display);font-weight:800;font-size:clamp(3rem,7vw,6rem);line-height:1;letter-spacing:-.04em;margin:0 0 .8rem;}
.mw-step h3,.mw-step .mw-step-title{font-family:var(--mw-display);font-weight:700;font-size:1.5rem;letter-spacing:-.02em;margin:0 0 .6rem;padding:0;color:var(--mw-text);}
.mw-step p{color:var(--mw-dim);font-size:1.02rem;line-height:1.6;max-width:52ch;margin:0;}
.mw-step p strong{color:var(--mw-text);}
@media (max-width:860px){.mw-pin{grid-template-columns:1fr;}.mw-pin-left{position:static;}}

/* ---- closing ---- */
.mw-closing{margin:clamp(5rem,16vh,10rem) 0 0;padding-top:2rem;border-top:1px solid var(--mw-line);}
.mw-closing .mw-chapter-title{max-width:18ch;}
.mw-closing p.mw-fine{color:var(--mw-dim);font-size:.9rem;line-height:1.6;max-width:84ch;margin:1.4rem 0 0;}

/* =====================================================================
   Motion. Everything below is optional polish.
   ===================================================================== */
@media (prefers-reduced-motion:no-preference){

  /* time-based: hero arrival */
  .mw-sky{animation:mw-fade 2.6s ease-out both;}
  .mw-sky i:nth-child(5n+1){animation:mw-twinkle 4.4s ease-in-out infinite alternate;}
  .mw-sky i:nth-child(7n+3){animation:mw-twinkle 6.3s ease-in-out -2s infinite alternate;}
  .mw-sky i:nth-child(11n+5){animation:mw-twinkle 3.1s ease-in-out -1s infinite alternate;}
  .mw-hero-inner > *{animation:mw-rise-in 1.1s cubic-bezier(.2,.7,.2,1) both;}
  .mw-hero-inner > *:nth-child(2){animation-delay:.12s;} .mw-hero-inner > *:nth-child(3){animation-delay:.24s;}
  .mw-hero-inner > *:nth-child(4){animation-delay:.36s;} .mw-hero-inner > *:nth-child(5){animation-delay:.48s;}
  .mw-hero-inner > *:nth-child(6){animation-delay:.6s;}
  .mw-meteors span{animation:mw-fall 8s linear infinite;}
  .mw-meteors span:nth-child(1){animation-delay:1.2s;} .mw-meteors span:nth-child(2){animation-delay:3.4s;}
  .mw-meteors span:nth-child(3){animation-delay:5.1s;} .mw-meteors span:nth-child(4){animation-delay:6.6s;}
  .mw-meteors span:nth-child(5){animation-delay:2.3s;} .mw-meteors span:nth-child(6){animation-delay:7.2s;}
  .mw-count{animation:mw-countup 2.4s cubic-bezier(.2,.7,.2,1) .6s both;}
  .mw-scrollcue span{animation:mw-cue 2.2s ease-in-out infinite;transform-origin:top;}

  /* scroll-driven: only where the browser supports it */
  @supports (animation-timeline:view()){
    .mw-hero .mw-hero-inner{animation:mw-away linear both;animation-timeline:view();animation-range:exit 0% exit 75%;}
    .mw-sky-wrap{animation:mw-drift linear both;animation-timeline:view();animation-range:exit 0% exit 100%;}

    .mw-statement .w{animation:mw-word linear both;animation-timeline:view();animation-range:entry 12% cover 34%;}

    .mw-reveal,.mw-chapter-head,.mw-key,.mw-cover,.mw-step,.mw-sheet,.mw-closing,
    [data-testid="stPlotlyChart"],[data-testid="stDataFrame"]{
      animation:mw-rise linear both;animation-timeline:view();animation-range:entry 0px entry 300px;}
    .mw-step-no{animation:mw-outline-fill linear both;animation-timeline:view();animation-range:entry 20% cover 45%;}
  }
}
@media (prefers-reduced-motion:reduce){
  .mw-count{counter-reset:mwn var(--mw-target);}
}

@keyframes mw-fade{from{opacity:0}to{opacity:1}}
@keyframes mw-twinkle{from{opacity:.45}to{opacity:1}}
@keyframes mw-rise-in{from{opacity:0;transform:translateY(34px)}to{opacity:1;transform:none}}
@keyframes mw-rise{from{opacity:0;transform:translateY(56px)}to{opacity:1;transform:none}}
@keyframes mw-away{to{opacity:0;transform:translateY(-12vh) scale(.97)}}
@keyframes mw-drift{to{transform:translateY(22vh)}}
@keyframes mw-word{from{opacity:.13}to{opacity:1}}
@keyframes mw-countup{from{--mw-n:0}to{--mw-n:var(--mw-target)}}
@keyframes mw-cue{0%,100%{transform:scaleY(.25);opacity:.4}50%{transform:scaleY(1);opacity:1}}
@keyframes mw-fall{
  0%{opacity:0;transform:translate(0,0) rotate(30deg)}
  4%{opacity:1}
  22%{opacity:0;transform:translate(-42vh,72vh) rotate(30deg)}
  100%{opacity:0;transform:translate(-42vh,72vh) rotate(30deg)}}
@keyframes mw-outline-fill{from{opacity:.25}to{opacity:1}}
"""


def theme_css() -> str:
    """The whole stylesheet, wrapped for ``st.markdown(..., unsafe_allow_html=True)``."""
    return f"<style>{_FONTS}{_TOKENS}{_COMPONENTS}{_STORY}</style>"
