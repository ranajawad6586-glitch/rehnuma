import { describe, expect, it } from "vitest";
import { formatPKR, humanStatus, shortAddress, sizeLabel } from "./format";

describe("format helpers", () => {
  it("formats PKR with thousands separators", () => {
    expect(formatPKR(185000)).toBe("Rs 185,000");
    expect(formatPKR(0)).toBe("Rs 0");
  });

  it("labels standard Bahria sizes", () => {
    expect(sizeLabel("10-marla")).toBe("10 Marla");
    expect(sizeLabel("1-kanal")).toBe("1 Kanal");
    expect(sizeLabel("unknown")).toBe("unknown");
  });

  it("humanizes status enums", () => {
    expect(humanStatus("CHAT_OPEN")).toBe("Chat open");
    expect(humanStatus("AGREEMENT_GENERATED")).toBe("Agreement generated");
  });

  it("builds a short address", () => {
    expect(shortAddress({ house_ref: "500-C", sector: "C", phase: "Phase 4" })).toBe(
      "House 500-C, Sector C, Phase 4",
    );
  });
});
