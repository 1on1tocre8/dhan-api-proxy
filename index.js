
const express = require('express');
const axios = require('axios');
const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());

// 🔐 Your Dhan credentials
const CLIENT_ID = 'ee3ea5d3';
const ACCESS_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzYwMjYzMTUyLCJpYXQiOjE3NjAxNzY3NTIsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA4NDgxOTUzIn0.Ib2ugYxTOE8OPovxHC8PzKzyT_BP4PAlMuqKuRFeSZm8fqqqdRgkw6qfAmDk6uimNV_R_sxGIcofH1JFwRyHVA';

// 📊 Get LTP
app.post('/get-ltp', async (req, res) => {
  try {
    const response = await axios.post('https://api.dhan.co/marketfeed/ltp', req.body, {
      headers: {
        'access-token': ACCESS_TOKEN,
        'client-id': CLIENT_ID,
      },
    });
    res.json(response.data);
  } catch (error) {
    res.status(error.response?.status || 500).json({ error: error.message });
  }
});

// 📊 Get OHLC
app.post('/get-ohlc', async (req, res) => {
  try {
    const response = await axios.post('https://api.dhan.co/marketfeed/ohlc', req.body, {
      headers: {
        'access-token': ACCESS_TOKEN,
        'client-id': CLIENT_ID,
      },
    });
    res.json(response.data);
  } catch (error) {
    res.status(error.response?.status || 500).json({ error: error.message });
  }
});

// 📊 Get Option Chain
app.post('/get-optionchain', async (req, res) => {
  try {
    const response = await axios.post('https://api.dhan.co/optionchain', req.body, {
      headers: {
        'access-token': ACCESS_TOKEN,
        'client-id': CLIENT_ID,
      },
    });
    res.json(response.data);
  } catch (error) {
    res.status(error.response?.status || 500).json({ error: error.message });
  }
});

// 📊 Get Intraday
app.post('/get-intraday', async (req, res) => {
  try {
    const response = await axios.post('https://api.dhan.co/charts/intraday', req.body, {
      headers: {
        'access-token': ACCESS_TOKEN,
        'client-id': CLIENT_ID,
      },
    });
    res.json(response.data);
  } catch (error) {
    res.status(error.response?.status || 500).json({ error: error.message });
  }
});

app.listen(PORT, () => {
  console.log(`Dhan Proxy API running on http://localhost:${PORT}`);
});
