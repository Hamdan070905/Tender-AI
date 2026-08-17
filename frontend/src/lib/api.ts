const API_BASE = "http://127.0.0.1:8000/api";

export const api = {
  getHeaders(): Record<string, string> {
    const token = localStorage.getItem("token");
    return token ? { "Authorization": `Bearer ${token}` } : {};
  },

  async getTenders() {
    const res = await fetch(`${API_BASE}/tenders`, {
      headers: this.getHeaders(),
    });

    if (!res.ok) {
      throw new Error(`HTTP Error: ${res.status}`);
    }

    const data = await res.json();
    return Array.isArray(data) ? data : (data.tenders || []);
  },

  async triggerSearch(query: string) {
    const res = await fetch(
      `${API_BASE}/tenders/crawl/trigger?query=${encodeURIComponent(query)}`,
      {
        method: "POST",
      }
    );

    return await res.json();
  },

  async draftProposal(tenderId: string) {
    const res = await fetch(
      `${API_BASE}/proposals/generate`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          tender_id: tenderId,
        }),
      }
    );

    return await res.json();
  }
};