const express = require("express");
const axios = require("axios");
const bodyParser = require("body-parser");

const app = express();
const port = process.env.PORT || 3000;

app.use(bodyParser.json());

const API_KEY = "ee3ea5d3";
const ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzYwMjYzMTUyLCJpYXQiOjE3NjAxNzY3NTIsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA4NDgxOTUzIn0.Ib2ugYxTOE8OPovxHC8PzKzyT_BP4PAlMuqKuRFeSZm8fqqqdRgkw6qfAmDk6uimNV_R_sxGIcofH1JFwRyHVA";

const headers = {
  "access-token": ACCESS_TOKEN,
  "client-id": API_KEY,
  "Content-Type": "application/json"
};

const base = "https://api.dhan.co";

app.post("/get-ltp", async (req, res) => {
  try {
    const response = await axios.post(`${base}/marketfeed/ltp`, req.body, { headers });
    res.json(response.data);
  } catch (err) {
    res.status(500).send(err.message);
  }
});

app.post("/get-ohlc", async (req, res) => {
  try {
    const response = await axios.post(`${base}/marketfeed/ohlc`, req.body, { headers });
    res.json(response.data);
  } catch (err) {
    res.status(500).send(err.message);
  }
});

app.post("/get-optionchain", async (req, res) => {
  try {
    const response = await axios.post(`${base}/optionchain`, req.body, { headers });
    res.json(response.data);
  } catch (err) {
    res.status(500).send(err.message);
  }
});

app.post("/get-intraday", async (req, res) => {
  try {
    const response = await axios.post(`${base}/charts/intraday`, req.body, { headers });
    res.json(response.data);
  } catch (err) {
    res.status(500).send(err.message);
  }
});

app.post("/get-id-by-symbol", async (req, res) => {
  const { symbol, segment } = req.body;
  try {
    const response = await axios.get(`${base}/instrument/${segment}`, { headers });
    const matches = response.data.filter(item => item.tradingSymbol === symbol);
    if (matches.length > 0) {
      res.json(matches[0]);
    } else {
      res.status(404).json({ error: "Symbol not found" });
    }
  } catch (err) {
    res.status(500).send(err.message);
  }
});

app.listen(port, () => {
  console.log(`Proxy running on port ${port}`);
});