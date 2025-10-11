const express = require('express');
const axios = require('axios');
const bodyParser = require('body-parser');
require('dotenv').config();

const app = express();
app.use(bodyParser.json());

const BASE_URL = 'https://api.dhan.co';
const ACCESS_TOKEN = process.env.ACCESS_TOKEN;
const API_KEY = process.env.API_KEY;

const HEADERS = {
  'access-token': ACCESS_TOKEN,
  'client-id': API_KEY,
};

app.get('/', (req, res) => {
  res.send('✅ Dhan Proxy API is running');
});

// Get Last Traded Price
app.post('/get-ltp', async (req, res) => {
  try {
    const response = await axios.post(`${BASE_URL}/marketfeed/ltp`, req.body, { headers: HEADERS });
    res.json(response.data);
  } catch (error) {
    res.status(500).json({ error: error.toString() });
  }
});

// Get OHLC
app.post('/get-ohlc', async (req, res) => {
  try {
    const response = await axios.post(`${BASE_URL}/marketfeed/ohlc`, req.body, { headers: HEADERS });
    res.json(response.data);
  } catch (error) {
    res.status(500).json({ error: error.toString() });
  }
});

// Get Intraday
app.post('/get-intraday', async (req, res) => {
  try {
    const response = await axios.post(`${BASE_URL}/charts/intraday`, req.body, { headers: HEADERS });
    res.json(response.data);
  } catch (error) {
    res.status(500).json({ error: error.toString() });
  }
});

// Get Option Chain
app.post('/get-option-chain', async (req, res) => {
  try {
    const response = await axios.post(`${BASE_URL}/optionchain`, req.body, { headers: HEADERS });
    res.json(response.data);
  } catch (error) {
    res.status(500).json({ error: error.toString() });
  }
});

const PORT = process.env.PORT || 10000;
app.listen(PORT, () => {
  console.log(`✅ Proxy running on port ${PORT}`);
});
