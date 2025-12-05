from typing import List, Dict, Any
from search_engine import search_web, pro_multi_search


def _severity_for_text(text: str) -> int:
    """
    Calcola la severity (0,1,2,3) in base alle parole chiave trovate
    nel titolo/snippet. Testo e parole chiave sono tutte in lower case.
    """
    text = text.lower()
    severity = 0

    # livello 3: reati molto gravi / violenza / terrorismo / abusi pesanti
    lvl3 = [
        "omicidio",
        "assassinio",
        "murder",
        "homicide",
        "tentato omicidio",
        "attempted murder",
        "stupro",
        "rape",
        "violent rape",
        "gang rape",
        "violenza sessuale",
        "sexual assault",
        "abuso sessuale",
        "sexual abuse",
        "pedofilia",
        "pedophilia",
        "paedophilia",
        "child abuse",
        "child sexual abuse",
        "abuso su minori",
        "molestation",
        "molestie sessuali",
        "sexual misconduct",
        "violenza domestica",
        "domestic violence",
        "family violence",
        "brutal assault",
        "aggravated assault",
        "aggressione grave",
        "rapina a mano armata",
        "armed robbery",
        "terrorismo",
        "terrorism",
        "terrorist attack",
        "attentato",
        "bombing",
        "mass shooting",
        "school shooting",
        "sequestro di persona",
        "kidnapping",
        "kidnap",
        "abduction",
        "hostage taking",
        "tortura",
        "torture",
        "tortured",
        "traffico di droga",
        "drug trafficking",
        "traffico di armi",
        "arms trafficking",
        "human trafficking",
        "traffico di esseri umani",
        "criminal gang",
        "criminal organization",
        "organized crime",
        "mafia",
        "camorra",
        "ndrangheta",
        "cartel",
        "drug cartel",
        "serial killer",
        "serial murderer",
        "massacro",
        "mass murder",
        "genocidio",
        "genocide",
    ]
    if any(w in text for w in lvl3):
        return 3

    # livello 2: frodi, corruzione, riciclaggio, reati finanziari seri / white collar pesanti
    lvl2 = [
        "truffa",
        "truffatore",
        "truffatori",
        "frode",
        "frodi",
        "fraud",
        "frauds",
        "scam",
        "scams",
        "scammer",
        "scammers",
        "ponzi",
        "ponzi scheme",
        "pyramid scheme",
        "riciclaggio",
        "riciclaggio di denaro",
        "money laundering",
        "laundered money",
        "evasione fiscale",
        "tax evasion",
        "tax fraud",
        "frode fiscale",
        "fiscal fraud",
        "false accounting",
        "bilanci falsi",
        "accounting fraud",
        "securities fraud",
        "wire fraud",
        "bank fraud",
        "insurance fraud",
        "credit card fraud",
        "mortgage fraud",
        "investment fraud",
        "appropriazione indebita",
        "embezzlement",
        "embezzled",
        "malversazione",
        "misappropriation",
        "self dealing",
        "self-dealing",
        "insider trading",
        "market manipulation",
        "manipolazione di mercato",
        "aggiotaggio",
        "price fixing",
        "bid rigging",
        "bancarotta fraudolenta",
        "bankruptcy fraud",
        "corruzione",
        "corruption",
        "bribery",
        "kickback",
        "kickbacks",
        "tangente",
        "tangenti",
        "concussione",
        "racketeering",
        "criminal conspiracy",
        "associazione a delinquere",
        "associazione mafiosa",
        "organized crime",
        "frode assicurativa",
        "insurance scam",
        "frode bancaria",
        "conflict of interest",
        "conflitto di interessi",
        "false dichiarazioni",
        "false statements",
        "forgery",
        "documenti falsi",
        "falsificazione di documenti",
        "false invoicing",
        "phishing scam",
        "investment scheme",
    ]
    if any(w in text for w in lvl2):
        severity = max(severity, 2)

    # livello 1: sanzioni, indagini, controversie, cause civili, default, problemi regolatori, reclami
    lvl1 = [
        "sanzione",
        "sanzioni",
        "sanction",
        "sanctions",
        "administrative sanction",
        "regulatory sanction",
        "multa",
        "multe",
        "fine ",
        "fined",
        "civil penalty",
        "administrative penalty",
        "enforcement action",
        "enforcement proceeding",
        "azioni di enforcement",
        "provvedimento disciplinare",
        "disciplinary action",
        "disciplinary measures",
        "indagine",
        "indagini",
        "investigation",
        "investigations",
        "inquiry",
        "inquiries",
        "probe",
        "regulatory probe",
        "avviso di garanzia",
        "proceedings",
        "disciplinary proceedings",
        "regulatory proceedings",
        "controversia",
        "controversie",
        "controversy",
        "controversial",
        "scandalo",
        "scandali",
        "scandal",
        "scandal-hit",
        "allegations",
        "allegation",
        "accuse",
        "accusations",
        "accusato",
        "accused",
        "charged with",
        "criminal charge",
        "criminal charges",
        "indicted",
        "indictment",
        "condanna",
        "condannato",
        "convicted",
        "conviction",
        "sentenced",
        "sentencing",
        "class action",
        "class-action",
        "lawsuit",
        "lawsuits",
        "cause legale",
        "cause legali",
        "legal action",
        "legal dispute",
        "legal battle",
        "litigation",
        "arbitrato",
        "arbitration",
        "settlement",
        "out-of-court settlement",
        "patteggiamento",
        "plea deal",
        "consent order",
        "warning letter",
        "richiamo ufficiale",
        "regulatory warning",
        "product recall",
        "richiamo prodotto",
        "revoca della licenza",
        "license revoked",
        "license revocation",
        "license suspension",
        "license suspended",
        "authorization withdrawn",
        "autorizzazione revocata",
        "banned",
        "blacklisted",
        "debarred",
        "watchlist",
        "blacklist",
        "default",
        "loan default",
        "insolvenza",
        "insolvent",
        "insolvency",
        "fallimento",
        "bankruptcy",
        "chapter 11",
        "chapter 7",
        "liquidazione",
        "liquidation",
        "liquidazione giudiziale",
        "procedura concorsuale",
        "amministrazione controllata",
        "receivership",
        "restructuring",
        "ristrutturazione del debito",
        "cease and desist",
        "injunction",
        "court order",
        "sequestro conservativo",
        "pignoramento",
        "foreclosure",
        "regulatory warning",
        "regulatory action",
        "regulatory fine",
        "consob",
        "ivass",
        "banca d'italia",
        "banca ditalia",
        "antitrust",
        "authority fine",
        "authority sanction",
        "complaint",
        "complaints",
        "reclamo",
        "reclami",
        "customer complaint",
        "esposto",
        "denuncia",
        "whistleblower",
        "whistleblowing",
    ]
    if any(w in text for w in lvl1):
        severity = max(severity, 1)

    return severity


def analyze_reputation(query: str, max_results: int = 100) -> Dict[str, Any]:
    """
    Motore reputazionale base (consumer):
    - usa SOLO la query base (nome / azienda) su Google Programmable Search
    - prende fino a 100 risultati
    - analizza titolo+snippet con una lista di parole negative ita/eng
    - calcola score 0-100 e livello LOW / MEDIUM / HIGH
    """
    max_results = 100

    data = search_web(query, max_results=max_results)
    raw_results = data.get("results", [])

    analyzed: List[Dict[str, Any]] = []
    score = 0

    name_tokens = [t for t in query.lower().split() if len(t) > 2]

    for item in raw_results:
        title = item.get("title", "") or ""
        snippet = item.get("snippet", "") or ""
        url = item.get("url", "") or ""
        text = (title + " " + snippet).lower()

        if name_tokens and not any(t in text for t in name_tokens):
            severity = 0
        else:
            severity = _severity_for_text(text)

        if severity == 3:
            score += 12
        elif severity == 2:
            score += 7
        elif severity == 1:
            score += 3

        analyzed.append(
            {
                "title": title,
                "url": url,
                "snippet": snippet,
                "severity": severity,
            }
        )

    if score > 100:
        score = 100
    if score < 0:
        score = 0

    if score >= 70:
        level = "HIGH"
    elif score >= 30:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "query": query,
        "score": score,
        "level": level,
        "total_results": len(analyzed),
        "results": analyzed,
    }


def analyze_reputation_pro(query: str, max_total: int = 150) -> Dict[str, Any]:
    """
    Modalita PRO:
    - esegue piu query mirate (pro_multi_search)
    - deduplica per URL
    - usa il dizionario 'panda' per severity
    - calcola score 0-100
    - conteggia quanti link negativi per livello
    - restituisce solo un sottoinsieme strutturato pronto per PDF/report.
    """
    max_total = max_total or 150

    raw_results = pro_multi_search(query, max_total=max_total)

    analyzed: List[Dict[str, Any]] = []
    score = 0

    by_severity = {"3": 0, "2": 0, "1": 0}
    negative_count = 0

    for item in raw_results:
        title = item.get("title", "") or ""
        snippet = item.get("snippet", "") or ""
        url = item.get("url", "") or ""
        source_query = item.get("source_query", "") or ""
        text = (title + " " + snippet).lower()

        severity = _severity_for_text(text)

        if severity > 0:
            negative_count += 1
            by_severity[str(severity)] += 1

        if severity == 3:
            score += 12
        elif severity == 2:
            score += 7
        elif severity == 1:
            score += 3

        analyzed.append(
            {
                "title": title,
                "url": url,
                "snippet": snippet,
                "severity": severity,
                "source_query": source_query,
            }
        )

    if score > 100:
        score = 100
    if score < 0:
        score = 0

    if score >= 70:
        level = "HIGH"
    elif score >= 30:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "query": query,
        "mode": "pro",
        "score": score,
        "level": level,
        "total_results": len(analyzed),
        "negative_links_count": negative_count,
        "by_severity": by_severity,
        "results": analyzed,
    }