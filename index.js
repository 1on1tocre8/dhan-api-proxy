require("dotenv").config();
const express = require("express");
const axios = require("axios");
const cors = require("cors");

const app = express();
app.use(cors());
app.use(express.json());

const API_KEY = process.env.API_KEY;
const ACCESS_TOKEN = process.env.ACCESS_TOKEN;
const BASE_URL = "https://api.dhan.co";

app.post("/get-ltp", async (req, res) => {
  try {
    const payload = req.body; // Expect: { "NSE_EQ": [11536] }
    console.log("Calling Dhan LTP with payload:", payload);

    const response = await axios.post(`${BASE_URL}/marketfeed/ltp`, payload, {
      headers: {
        "access-token": ACCESS_TOKEN,
        "client-id": API_KEY,
      },
    });

    console.log("✅ LTP response:", response.data);
    res.json(response.data);
  } catch (error) {
    console.error("❌ Error fetching LTP from Dhan");
    console.error("Status:", error.response?.status);
    console.error("Response data:", error.response?.data);
    res
      .status(error.response?.status || 500)
      .json({ error: error.response?.data || "Unexpected error" });
  }
});

app.post("/get-ohlc", async (req, res) => {
  try {
    const payload = req.body; // Expect: { "NSE_EQ": [id] }
    console.log("Calling Dhan OHLC with payload:", payload);

    const response = await axios.post(`${BASE_URL}/marketfeed/ohlc`, payload, {
      headers: {
        "access-token": ACCESS_TOKEN,
        "client-id": API_KEY,
      },
    });

    console.log("✅ OHLC response:", response.data);
    res.json(response.data);
  } catch (error) {
    console.error("❌ Error fetching OHLC from Dhan");
    console.error("Status:", error.response?.status);
    console.error("Response data:", error.response?.data);
    res
      .status(error.response?.status || 500)
      .json({ error: error.response?.data || "Unexpected error" });
  }
});

app.listen(10000, () => {
  console.log("✅ Proxy running on port 10000");
});
