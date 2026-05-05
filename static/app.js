const openapiPath = "/openapi.json";
console.log("Discovery endpoint:", openapiPath);

document.getElementById("create-api-key")?.addEventListener("click", async () => {
  const r = await fetch("/api/key", { method: "POST", credentials: "same-origin" });
  const data = await r.json();
  document.getElementById("api-key-display").textContent = data.api_key || "N/A";
  document.getElementById("api-result").textContent = JSON.stringify(data, null, 2);
});

document.getElementById("api-withdraw-test")?.addEventListener("click", async () => {
  const r = await fetch("/api/withdraw", { method: "POST", headers: {"Content-Type":"application/json", "X-API-KEY":"API-user-1234"}, body: JSON.stringify({amount: 1000}) });
  document.getElementById("api-result").textContent = JSON.stringify(await r.json(), null, 2);
});

document.getElementById("withdraw-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const r = await fetch("/withdraw", { method: "POST", body: new URLSearchParams(fd) });
  document.getElementById("withdraw-result").textContent = JSON.stringify(await r.json(), null, 2);
});
