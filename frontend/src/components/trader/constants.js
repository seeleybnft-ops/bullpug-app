const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const TRADING_BOT_IMAGE = "https://customer-assets.emergentagent.com/job_eece36b0-bd7c-41e3-9663-864558bfa54c/artifacts/79azcfdc_image%20-%202026-03-04T094746.318.jpg";

const AUTO_SCAN_INTERVAL = 5 * 60 * 1000;

const TOKENS = {
  SOL: "So11111111111111111111111111111111111111112",
  USDC: "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
  BONK: "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
  WIF: "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
  JUP: "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
};

const RISK_COLORS = {
  safer: { bg: "bg-[#00FFA3]/10", text: "text-[#00FFA3]", border: "border-[#00FFA3]/30" },
  high_risk: { bg: "bg-[#FF6B6B]/10", text: "text-[#FF6B6B]", border: "border-[#FF6B6B]/30" }
};

export { API, TRADING_BOT_IMAGE, AUTO_SCAN_INTERVAL, TOKENS, RISK_COLORS };
