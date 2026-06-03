"""Render the tenancy agreement and police verification form to PDF.

HTML building is pure (no third-party imports) so it is unit-testable without WeasyPrint.
The actual PDF rasterization imports WeasyPrint lazily inside html_to_pdf(), keeping module
import light and letting the rest of the app load even where WeasyPrint isn't installed.
Layout targets an A4 stamp-paper sheet.
"""
from __future__ import annotations

import html

_PAGE_CSS = """
@page { size: A4; margin: 2.2cm 2cm; }
body { font-family: 'DejaVu Serif', serif; font-size: 11pt; color: #1a1a1a; line-height: 1.5; }
h1 { font-size: 16pt; text-align: center; letter-spacing: 1px; margin-bottom: 2pt; }
.sub { text-align: center; font-size: 9pt; color: #555; margin-bottom: 16pt; }
.meta { font-size: 9pt; color: #555; }
h2 { font-size: 11pt; margin: 14pt 0 4pt; border-bottom: 1px solid #ccc; padding-bottom: 2pt; }
ol { margin: 0; padding-left: 18pt; }
li { margin-bottom: 6pt; }
.terms td { padding: 3pt 8pt; vertical-align: top; }
.terms td.k { color: #555; width: 38%; }
.advisories { font-size: 9pt; background: #f6f3ea; padding: 8pt 10pt; }
.sign { margin-top: 30pt; }
.sign td { width: 50%; padding-top: 28pt; }
.line { border-top: 1px solid #333; padding-top: 3pt; font-size: 9pt; }
.blank { display: inline-block; min-width: 200pt; border-bottom: 1px solid #888; }
"""


def _esc(v) -> str:
    return html.escape(str(v if v is not None else ""))


def build_agreement_html(ctx: dict) -> str:
    rent = ctx["rent"]
    advance_amount = rent * ctx["advance_months"]
    advisories = "".join(f"<li>{_esc(a)}</li>" for a in ctx["advisories"])
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{_PAGE_CSS}</style></head><body>
<h1>TENANCY AGREEMENT</h1>
<div class="sub">Bahria Town Islamabad &middot; generated via RehnumaRent (dealer-free)</div>
<p class="meta">Date: {_esc(ctx['date'])}</p>

<p>This Tenancy Agreement is made between
<b>{_esc(ctx['owner_name'])}</b> (the &ldquo;Owner/Landlord&rdquo;) and
<b>{_esc(ctx['tenant_name'])}</b> (the &ldquo;Tenant&rdquo;) for the premises described below.</p>

<h2>1. Premises</h2>
<p>House <b>{_esc(ctx['house_ref'])}</b>, {_esc(ctx['sector'])}, Bahria Town Islamabad
&mdash; a {_esc(ctx['size'])} house.</p>

<h2>2. Terms</h2>
<table class="terms">
<tr><td class="k">Monthly rent</td><td><b>Rs {rent:,}</b> per month</td></tr>
<tr><td class="k">Advance</td><td><b>{_esc(ctx['advance_months'])} month(s)</b> (Rs {advance_amount:,})</td></tr>
<tr><td class="k">Security deposit</td><td><b>Rs {ctx['security']:,}</b> (refundable)</td></tr>
<tr><td class="k">Term</td><td><b>{_esc(ctx['duration_months'])} months</b> from {_esc(ctx['move_in'])}</td></tr>
<tr><td class="k">Notice to vacate</td><td><b>{_esc(ctx['notice_weeks'])} weeks</b> written notice by either party</td></tr>
</table>

<h2>3. Conditions</h2>
<ol>
<li>Rent is payable monthly in advance.</li>
<li>All Bahria Town maintenance dues shall be confirmed cleared before possession is handed over.</li>
<li>The security deposit is refundable at the end of the term, less any agreed deductions.</li>
<li>Either party may terminate with {_esc(ctx['notice_weeks'])} weeks&rsquo; written notice.</li>
<li>The Tenant shall use the premises for lawful residential purposes only.</li>
</ol>

<h2>4. Stamp duty &amp; legal note</h2>
<p>Computed stamp duty band (annual rent <b>Rs {ctx['annual_rent']:,}</b>):
<b>{_esc(ctx['stamp_duty_label'])}</b>.</p>
<ul class="advisories">{advisories}</ul>

<table class="sign">
<tr>
<td><div class="line">Owner / Landlord: {_esc(ctx['owner_name'])}</div></td>
<td><div class="line">Tenant: {_esc(ctx['tenant_name'])}</div></td>
</tr>
<tr>
<td><div class="line">Witness 1</div></td>
<td><div class="line">Witness 2</div></td>
</tr>
</table>
</body></html>"""


def build_police_verification_html(ctx: dict) -> str:
    """Pre-filled with what we know; sensitive fields (CNIC, father's name) left blank to fill
    by hand — we never handle the counter-party's raw CNIC (rule 7)."""
    blank = '<span class="blank"></span>'
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{_PAGE_CSS}</style></head><body>
<h1>TENANT VERIFICATION FORM</h1>
<div class="sub">For submission to the local police station &middot; Bahria Town Islamabad</div>
<p class="meta">Date: {_esc(ctx['date'])}</p>

<h2>Property</h2>
<p>House <b>{_esc(ctx['house_ref'])}</b>, {_esc(ctx['sector'])}, Bahria Town Islamabad
({_esc(ctx['size'])}). Tenancy term: <b>{_esc(ctx['duration_months'])} months</b> from {_esc(ctx['move_in'])}.</p>

<h2>Owner / Landlord</h2>
<table class="terms">
<tr><td class="k">Name</td><td><b>{_esc(ctx['owner_name'])}</b></td></tr>
<tr><td class="k">CNIC</td><td>{blank}</td></tr>
<tr><td class="k">Contact no.</td><td>{blank}</td></tr>
</table>

<h2>Tenant</h2>
<table class="terms">
<tr><td class="k">Name</td><td><b>{_esc(ctx['tenant_name'])}</b></td></tr>
<tr><td class="k">CNIC</td><td>{blank}</td></tr>
<tr><td class="k">Father&rsquo;s name</td><td>{blank}</td></tr>
<tr><td class="k">Permanent address</td><td>{blank}</td></tr>
<tr><td class="k">Contact no.</td><td>{blank}</td></tr>
<tr><td class="k">No. of occupants</td><td>{blank}</td></tr>
</table>

<p style="margin-top:24pt">Police verification is a legal requirement for tenancies. Complete the
blank fields, attach CNIC copies, and submit to the local police station.</p>

<table class="sign"><tr>
<td><div class="line">Owner signature</div></td>
<td><div class="line">Tenant signature</div></td>
</tr></table>
</body></html>"""


def html_to_pdf_bytes(html_str: str) -> bytes:
    """Render HTML to PDF bytes (for upload to object storage). Imports WeasyPrint lazily."""
    from weasyprint import HTML  # heavy import deferred to call time

    return HTML(string=html_str).write_pdf()
