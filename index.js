const express = require("express");
const axios = require("axios");
const app = express();

app.use(express.json());

const PORT = process.env.PORT || 10000;

// Load your Dhan API credentials from environment or hardcode for testing
const API_KEY = process.env.DHAN_API_KEY || "ee3ea5d3";
const ACCESS_TOKEN = process.env.DHAN_ACCESS_TOKEN || "your_access_token_here";

// Headers used in all Dhan API requests
const getAuthHeaders = () => ({
  "access-token": ACCESS_TOKEN,
  "client-id": API_KEY,
  "Content-Type": "application/json",
});

// Base URL
const DHAN_API_BASE = "https://api.dhan.co";

// === ROUTES ===

// 📈 Get LTP (Last Traded Price)
app.post("/get-ltp", async (req, res) => {
  try {
    const response = await axios.post(
      `${DHAN_API_BASE}/marketfeed/ltp`,
      req.body,
      { headers: getAuthHeaders() }
    );
    res.json(response.data);
  } catch (error) {
    console.error("LTP error:", error?.response?.data || error.message);
    res.status(500).json({ error: "Failed to fetch LTP", details: error?.response?.data });
  }
});

// 📊 Get OHLC
app.post("/get-ohlc", async (req, res) => {
  try {
    const response = await axios.post(
      `${DHAN_API_BASE}/marketfeed/ohlc`,
      req.body,
      { headers: getAuthHeaders() }
    );
    res.json(response.data);
  } catch (error) {
    console.error("OHLC error:", error?.response?.data || error.message);
    res.status(500).json({ error: "Failed to fetch OHLC", details: error?.response?.data });
  }
});

// 📉 Get Intraday Chart
app.post("/get-intraday", async (req, res) => {
  try {
    const response = await axios.post(
      `${DHAN_API_BASE}/charts/intraday`,
      req.body,
      { headers: getAuthHeaders() }
    );
    res.json(response.data);
  } catch (error) {
    console.error("Intraday error:", error?.response?.data || error.message);
    res.status(500).json({ error: "Failed to fetch Intraday chart", details: error?.response?.data });
  }
});

// 🧾 Get Option Chain
app.post("/get-option-chain", async (req, res) => {
  try {
    const response = await axios.post(
      `${DHAN_API_BASE}/optionchain`,
      req.body,
      { headers: getAuthHeaders() }
    );
    res.json(response.data);
  } catch (error) {
    console.error("Option Chain error:", error?.response?.data || error.message);
    res.status(500).json({ error: "Failed to fetch Option Chain", details: error?.response?.data });
  }
});

// 🟢 Default route
app.get("/", (req, res) => {
  res.send("✅ Dhan Proxy is running.");
});

// Start server
app.listen(PORT, () => {
  console.log(`✅ Proxy running on port ${PORT}`);
});
