const express = require('express');
const axios = require('axios');
const dotenv = require('dotenv');
const cors = require('cors');

dotenv.config();

const app = express();
const PORT = process.env.PORT || 10000;

app.use(cors());
app.use(express.json());

// LTP API
app.post('/get-ltp', async (req, res) => {
  try {
    const response = await axios.post(
      'https://api.dhan.co/marketfeed/ltp',
      req.body,
      {
        headers: {
          'access-token': process.env.ACCESS_TOKEN,
          'client-id': process.env.API_KEY,
        },
      }
    );
    res.json(response.data);
  } catch (error) {
    res.status(500).json({ error: error?.response?.data || error.message });
  }
});

// OHLC API
app.post('/get-ohlc', async (req, res) => {
  try {
    const response = await axios.post(
      'https://api.dhan.co/marketfeed/ohlc',
      req.body,
      {
        headers: {
          'access-token': process.env.ACCESS_TOKEN,
          'client-id': process.env.API_KEY,
        },
      }
    );
    res.json(response.data);
  } catch (error) {
    res.status(500).json({ error: error?.response?.data || error.message });
  }
});

// Intraday Chart
app.post('/get-intraday', async (req, res) => {
  try {
    const response = await axios.post(
      'https://api.dhan.co/charts/intraday',
      req.body,
      {
        headers: {
          'access-token': process.env.ACCESS_TOKEN,
          'client-id': process.env.API_KEY,
        },
      }
    );
    res.json(response.data);
  } catch (error) {
    res.status(500).json({ error: error?.response?.data || error.message });
  }
});

// Option Chain
app.post('/get-option-chain', async (req, res) => {
  try {
    const response = await axios.post(
      'https://api.dhan.co/optionchain',
      req.body,
      {
        headers: {
          'access-token': process.env.ACCESS_TOKEN,
          'client-id': process.env.API_KEY,
        },
      }
    );
    res.json(response.data);
  } catch (error) {
    res.status(500).json({ error: error?.response?.data || error.message });
  }
});

app.listen(PORT, () => {
  console.log(`✅ Proxy running on port ${PORT}`);
});
