"""Fictional SEC-style filing excerpts, one document per section.

Hand-written excerpts back the planted stories in universe.EVENTS. Every other company gets a
templated quarterly report so semantic search has something to find for the whole universe.
"""
from universe import COMPANIES

_BY_SYM = {c["sym"]: c for c in COMPANIES}

STORY_FILINGS = [
    # --- ORCH: prior 10-Q (baseline) and the new 10-K, so analysts can ask what changed ---
    dict(sym="ORCH", form="10-Q", filed="2026-05-01T20:05:00Z", period="2026-03-31",
         section="Risk Factors", title="Orchard Devices 10-Q Q3 FY2026 - Risk Factors",
         content="There have been no material changes to the risk factors disclosed in our most recent "
                 "annual report. We continue to depend on a limited number of contract manufacturers "
                 "for final assembly of our devices. Demand for our products is sensitive to consumer "
                 "spending and to the timing of new product introductions. Fluctuations in foreign "
                 "currency exchange rates, particularly the euro and the yen, affect reported net sales."),
    dict(sym="ORCH", form="10-K", filed="2026-09-22T11:00:00Z", period="2026-06-30",
         section="Risk Factors - Supply Chain",
         title="Orchard Devices 10-K FY2026 - Supply chain concentration",
         content="Substantially all of our hardware products are assembled by outsourcing partners located "
                 "in a single geographic region, and approximately 70 percent of the advanced displays used "
                 "in our flagship devices come from two suppliers. During fiscal 2026, an earthquake-related "
                 "shutdown at one display supplier constrained flagship availability for six weeks. Trade "
                 "restrictions, export controls, or new tariffs affecting that region could materially "
                 "increase our costs or interrupt supply. We have begun qualifying assembly capacity in "
                 "two additional countries but do not expect it to exceed 15 percent of volume before "
                 "fiscal 2028. Component shortages, in particular for memory and advanced logic chips, "
                 "may reduce gross margin."),
    dict(sym="ORCH", form="10-K", filed="2026-09-22T11:00:00Z", period="2026-06-30",
         section="Risk Factors - Regulation",
         title="Orchard Devices 10-K FY2026 - AI and digital markets regulation",
         content="New rules governing artificial intelligence features, including on-device assistants, "
                 "may require us to change how models are trained, disclosed, or deployed in certain "
                 "jurisdictions, and could delay launches in the European Union. Digital markets "
                 "regulation now requires us to permit alternative app marketplaces and payment methods "
                 "in several countries. Services revenue, which represented 26 percent of net sales and a "
                 "higher share of gross margin, could decline if commission rates fall. We are also "
                 "subject to an antitrust investigation regarding default search and app store terms; "
                 "an adverse outcome could result in fines of up to 10 percent of global revenue."),
    dict(sym="ORCH", form="10-K", filed="2026-09-22T11:00:00Z", period="2026-06-30",
         section="MD&A", title="Orchard Devices 10-K FY2026 - Management's discussion and analysis",
         content="Net sales for fiscal 2026 were $410 billion, up 4 percent year over year. Devices revenue "
                 "grew 1 percent while services grew 13 percent. Gross margin was 45.8 percent, a decline "
                 "of 60 basis points driven by higher component costs and the six-week display supply "
                 "constraint. For fiscal 2027 we expect low single digit revenue growth, gross margin "
                 "between 45 and 46 percent, and capital expenditure of $14 billion, up from $11 billion, "
                 "reflecting investment in data centers for AI services and supply diversification."),

    # --- NVLT: 10-Q baseline and the export-control 8-K ---
    dict(sym="NVLT", form="10-Q", filed="2026-08-26T20:10:00Z", period="2026-07-26",
         section="MD&A", title="Novalight Semiconductor 10-Q Q2 FY2027 - Results",
         content="Revenue was $27.1 billion, up 58 percent year over year, led by data center accelerators, "
                 "which were 88 percent of revenue. Customers outside the United States accounted for "
                 "roughly 46 percent of data center revenue. Gross margin was 74.2 percent. Supply of "
                 "advanced packaging capacity remains the primary constraint on shipments, and we have "
                 "entered into multi-year purchase commitments of $31 billion."),
    dict(sym="NVLT", form="8-K", filed="2026-09-15T18:10:00Z", period="2026-09-15",
         section="Item 7.01 Regulation FD Disclosure",
         title="Novalight Semiconductor 8-K - Export license requirement",
         content="On September 15, 2026, the Company was informed by the U.S. government that a license is "
                 "now required to export its two most advanced accelerator families, and systems that "
                 "incorporate them, to customers in a group of countries that represented approximately "
                 "18 percent of data center revenue in the most recent quarter. The requirement is "
                 "effective immediately. The Company does not expect licenses to be granted for most "
                 "pending orders and now expects revenue for the third quarter of fiscal 2027 to be "
                 "approximately $4 billion lower than its prior outlook. The Company may also record "
                 "inventory and purchase commitment charges of up to $1.5 billion."),

    # --- VTRX: 10-Q with PDUFA date and the approval 8-K ---
    dict(sym="VTRX", form="10-Q", filed="2026-08-06T20:00:00Z", period="2026-06-30",
         section="Risk Factors", title="Vitrexa Therapeutics 10-Q Q2 2026 - Risk factors",
         content="We currently have no products approved for sale and depend entirely on the success of "
                 "VX-401, our oral therapy for moderate-to-severe ulcerative colitis. The FDA has assigned "
                 "a target action date under the Prescription Drug User Fee Act of September 26, 2026. "
                 "The FDA may not approve VX-401 on that date or at all, may require additional trials, "
                 "or may approve a label narrower than we seek, including a boxed warning related to "
                 "liver enzyme elevations observed in 3 percent of trial participants. As of June 30, "
                 "2026 we had cash of $1.2 billion, which we believe funds operations into 2028."),
    dict(sym="VTRX", form="8-K", filed="2026-09-24T11:30:00Z", period="2026-09-24",
         section="Item 8.01 Other Events", title="Vitrexa Therapeutics 8-K - FDA approval of VX-401",
         content="On September 24, 2026, two days ahead of its target action date, the U.S. Food and Drug "
                 "Administration approved VX-401 for adults with moderately to severely active ulcerative "
                 "colitis. The label does not include a boxed warning; liver enzyme monitoring is "
                 "recommended during the first twelve weeks of treatment. The Company expects commercial "
                 "launch in the fourth quarter of 2026 and will host an investor call at 8:30 a.m. ET."),

    # --- HRBR + KEYS: commercial real estate credit stress ---
    dict(sym="HRBR", form="8-K", filed="2026-09-09T15:45:00Z", period="2026-09-09",
         section="Item 2.02 Results of Operations",
         title="Harborview Bancorp 8-K - Mid-quarter credit update",
         content="Harborview Bancorp expects to record a provision for credit losses of $410 million to $460 "
                 "million for the third quarter of 2026, compared with $145 million in the second quarter. "
                 "The increase relates primarily to office loans in its commercial real estate portfolio, "
                 "where criticized balances rose to $2.3 billion and two large borrowers defaulted. Office "
                 "loans represent 9 percent of total loans. The Company also lowered its full-year net "
                 "interest income guidance to a decline of 3 to 4 percent, from a prior range of flat to "
                 "down 2 percent, reflecting higher deposit costs. The CET1 ratio remains above 10 percent."),
    dict(sym="KEYS", form="10-Q", filed="2026-08-04T20:15:00Z", period="2026-06-30",
         section="Risk Factors", title="Keystone Office REIT 10-Q Q2 2026 - Risk factors",
         content="Occupancy across our office portfolio was 81.4 percent, down from 84.0 percent a year ago. "
                 "Leases representing 11 percent of annualized base rent expire within the next eighteen "
                 "months. $1.9 billion of our mortgage debt matures in 2027, and refinancing may only be "
                 "available at substantially higher rates or lower loan-to-value ratios. Regional banks, "
                 "which provide a significant share of our secured financing, have tightened lending "
                 "standards for office properties."),

    # --- ROVR recall, LDGR leadership change, CRTL results ---
    dict(sym="ROVR", form="8-K", filed="2026-09-17T20:30:00Z", period="2026-09-17",
         section="Item 8.01 Other Events", title="Rover Motors 8-K - Voluntary recall",
         content="Rover Motors is voluntarily recalling approximately 120,000 Model S2 and Model T2 vehicles "
                 "built between March 2025 and January 2026 to replace a battery module connector that can "
                 "overheat under sustained fast charging. The Company is aware of 14 thermal incidents and "
                 "no injuries. The remedy requires a service visit of about three hours. The Company "
                 "estimates the cost of the recall at $650 million to $800 million, to be recognized in "
                 "the third quarter of 2026, and is pausing fast-charging rates above 150 kW for affected "
                 "vehicles through an over-the-air update until the repair is complete."),
    dict(sym="LDGR", form="8-K", filed="2026-09-29T12:00:00Z", period="2026-09-29",
         section="Item 5.02 Departure of Directors or Certain Officers",
         title="Ledger Pay 8-K - CEO transition",
         content="On September 28, 2026, Daniel Okafor notified the Board of his resignation as Chief "
                 "Executive Officer and director, effective immediately, for personal reasons. The Board "
                 "appointed Chief Financial Officer Priya Raman as interim CEO and has begun a search for "
                 "a permanent successor. Ledger Pay reaffirmed its third-quarter outlook of total payment "
                 "volume growth of 17 to 19 percent. The Company also disclosed that its Audit Committee "
                 "is reviewing the classification of certain merchant incentive payments."),
    dict(sym="CRTL", form="8-K", filed="2026-09-03T11:00:00Z", period="2026-08-01",
         section="Item 2.02 Results of Operations", title="Cartwheel Retail 8-K - Q2 results",
         content="Second-quarter comparable sales rose 4.1 percent, ahead of the 1.5 percent the Company had "
                 "guided, driven by a 9 percent increase in digital sales and same-day delivery. Operating "
                 "margin expanded 70 basis points to 5.9 percent on lower freight and markdown costs. "
                 "Inventory was 6 percent lower year over year. The Company raised full-year earnings per "
                 "share guidance to $4.70 to $4.95 from $4.30 to $4.60."),
]

_SECTOR_RISK = {
    "Technology": "Rapid technological change, customer concentration among large cloud providers, and "
                  "dependence on a small number of foundries could reduce demand or margins.",
    "Communication Services": "Advertising demand is cyclical, and content costs, privacy regulation, and "
                              "platform policy changes could reduce revenue per user.",
    "Consumer Discretionary": "Demand depends on consumer confidence, employment, and credit availability; "
                              "higher tariffs on imported goods could raise costs.",
    "Consumer Staples": "Input cost inflation for commodities and packaging, retailer consolidation, and the "
                        "growth of private-label products could pressure margins.",
    "Health Care": "Government pricing reforms, reimbursement changes, and product liability claims could "
                   "affect results; utilization trends may differ from assumptions.",
    "Financials": "Changes in interest rates, credit quality, and deposit competition affect earnings, and "
                  "catastrophe losses or fraud could exceed reserves.",
    "Energy": "Commodity price volatility, permitting delays, and changes to energy policy and tax credits "
              "could affect project returns and cash flow.",
    "Industrials": "Freight volumes, labor availability, supplier delays, and defense budget timing could "
                   "affect revenue and margins.",
    "Utilities": "Rate case outcomes, wildfire and storm exposure, and the cost of grid investment needed "
                 "for data center load growth could affect returns.",
    "Real Estate": "Higher interest rates, tenant demand for space, and refinancing risk could reduce "
                   "property values and funds from operations.",
}


def _templated_10q(c: dict) -> dict:
    return dict(
        sym=c["sym"], form="10-Q", filed="2026-08-07T20:00:00Z", period="2026-06-30",
        section="Risk Factors", title=f"{c['name']} 10-Q Q2 2026 - Risk factors",
        content=f"{c['name']} operates in the {c['industry'].lower()} industry. There have been no material "
                f"changes to our risk factors since our annual report. {_SECTOR_RISK[c['sector']]} Trailing "
                f"twelve-month revenue was ${c['revenue_ttm_bn']} billion.",
    )


def all_filings() -> list[dict]:
    docs = list(STORY_FILINGS)
    covered = {d["sym"] for d in docs}
    docs += [_templated_10q(c) for c in COMPANIES if c["sym"] not in covered]
    for i, d in enumerate(docs, 1):
        c = _BY_SYM[d["sym"]]
        d.update(company=c["name"], sector=c["sector"], accession=f"0009999{i:03d}-26-{i:06d}")
        # Prefix the searchable text with who/what/when so passages are self-describing.
        d["content"] = f"{c['name']} ({d['sym']}), Form {d['form']} filed {d['filed'][:10]}, {d['section']}. {d['content']}"
    return docs
