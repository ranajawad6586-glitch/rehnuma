export type User = {
  id: number;
  name: string | null;
  roles: string[];
  phone_verified: boolean;
  cnic_captured: boolean;
  created_at: string;
};

export type Listing = {
  id: number;
  owner_id: number;
  plot_id: number | null;
  phase: string;
  sector: string;
  house_ref: string;
  size: string;
  rent: number;
  beds: number;
  baths: number;
  status: string;
  photos: string[];
  created_at: string;
};

export type Contact = { name: string | null; phone: string | null };

export type Deal = {
  id: number;
  listing_id: number;
  tenant_id: number;
  owner_id: number;
  status: string;
  tenant_consent_contact: boolean;
  owner_consent_contact: boolean;
  contact_shared: boolean;
  contact: Contact | null;
  locked_terms: Record<string, unknown> | null;
  created_at: string;
};

export type Message = {
  id: number;
  deal_id: number;
  sender_id: number | null;
  body: string;
  type: string;
  created_at: string;
};

export type Offer = {
  id: number;
  deal_id: number;
  sender_id: number;
  rent: number;
  advance_months: number;
  security: number;
  duration_months: number;
  move_in: string;
  status: string;
  created_at: string;
};

export type Fairness = { verdict: string; is_fair: boolean; flags: string[] };

export type Agreement = {
  id: number;
  deal_id: number;
  stamp_duty_band: number;
  stamp_duty_label: string;
  annual_rent: number;
  notice_weeks: number;
  terms: Record<string, unknown>;
  advisories: string[];
  pdf_url: string;
  created_at: string;
};

export type AskResponse = {
  session_id: number;
  reply: string;
  provider: string;
  language: string;
  fell_back: boolean;
};
