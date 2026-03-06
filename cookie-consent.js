(function () {
  var GA_ID = "G-W96EZRN1MR";
  var CONSENT_KEY = "cookie_consent";
  var gaLoaded = false;
  var sessionConsent = null;

  function getConsent() {
    if (sessionConsent !== null) return sessionConsent;
    try {
      return localStorage.getItem(CONSENT_KEY);
    } catch (e) {
      return null;
    }
  }

  function setConsent(value) {
    sessionConsent = value;
    try {
      localStorage.setItem(CONSENT_KEY, value);
    } catch (e) {}
  }

  function loadGA() {
    if (gaLoaded) return;
    gaLoaded = true;

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
    setConsent("accepted");
    hideBanner();
    loadGA();
  }

  function declineCookies() {
    setConsent("declined");
    hideBanner();
  }

  function init() {
    var consent = getConsent();
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
