(function () {
  var GA_ID = "G-W96EZRN1MR";
  var CONSENT_KEY = "cookie_consent";

  function loadGA() {
    var script = document.createElement("script");
    script.src = "https://www.googletagmanager.com/gtag/js?id=" + GA_ID;
    script.async = true;
    document.head.appendChild(script);

    window.dataLayer = window.dataLayer || [];
    function gtag() {
      dataLayer.push(arguments);
    }
    gtag("js", new Date());
    gtag("config", GA_ID);
  }

  function hideBanner() {
    var banner = document.getElementById("cookie-banner");
    if (banner) banner.style.display = "none";
  }

  function showBanner() {
    var banner = document.getElementById("cookie-banner");
    if (banner) banner.style.display = "flex";
  }

  function acceptCookies() {
    localStorage.setItem(CONSENT_KEY, "accepted");
    hideBanner();
    loadGA();
  }

  function declineCookies() {
    localStorage.setItem(CONSENT_KEY, "declined");
    hideBanner();
  }

  function init() {
    var consent = localStorage.getItem(CONSENT_KEY);
    if (consent === "accepted") {
      loadGA();
    } else if (consent !== "declined") {
      showBanner();
    }
  }

  window.acceptCookies = acceptCookies;
  window.declineCookies = declineCookies;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
