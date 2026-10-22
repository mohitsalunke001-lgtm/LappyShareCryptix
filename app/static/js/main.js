/**
 * LappyShare Platform - Ultra-Modern Interactive Client Script
 * Bento Grid, Mouse Spotlight, 3D Tilt, Theme Switcher & Accordion
 */

document.addEventListener("DOMContentLoaded", function () {
  // 1. Initialize Lucide Icons
  if (typeof lucide !== "undefined") {
    lucide.createIcons();
  }

  // 2. Dark/Light Theme Switcher with LocalStorage
  const themeToggleBtn = document.getElementById("theme-toggle");
  if (themeToggleBtn) {
    themeToggleBtn.addEventListener("click", function () {
      const currentTheme = document.documentElement.getAttribute("data-theme") || "dark";
      const newTheme = currentTheme === "dark" ? "light" : "dark";
      
      document.documentElement.setAttribute("data-theme", newTheme);
      try {
        localStorage.setItem("lappyshare-theme", newTheme);
      } catch (e) {}

      // Re-render Lucide icons if needed
      if (typeof lucide !== "undefined") {
        lucide.createIcons();
      }
    });
  }

  // 3. Dynamic Cursor Spotlight Tracking (Linear / Vercel effect)
  const spotlightCards = document.querySelectorAll(
    ".bento-card, .laptop-card, .stat-card, .calc-glass-box, .hero-showcase-window"
  );
  
  spotlightCards.forEach(function (card) {
    card.addEventListener("mousemove", function (e) {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      card.style.setProperty("--mouse-x", `${x}px`);
      card.style.setProperty("--mouse-y", `${y}px`);
    });
  });

  // 4. Hero 3D Card Tilt Effect on Mouse Move
  const heroWindow = document.getElementById("hero-window");
  if (heroWindow) {
    const heroWrapper = heroWindow.closest(".hero-window-wrapper");
    if (heroWrapper) {
      heroWrapper.addEventListener("mousemove", function (e) {
        const rect = heroWrapper.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        const deltaX = (e.clientX - centerX) / (rect.width / 2);
        const deltaY = (e.clientY - centerY) / (rect.height / 2);

        const rotateY = deltaX * 8; // max 8 deg
        const rotateX = -deltaY * 8; // max 8 deg

        heroWindow.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.01, 1.01, 1.01)`;
      });

      heroWrapper.addEventListener("mouseleave", function () {
        heroWindow.style.transform = "perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)";
      });
    }
  }

  // 5. Interactive Hardware Fleet Category Filter Chips
  const filterBtns = document.querySelectorAll(".filter-chip-btn");
  const laptopCards = document.querySelectorAll("#featured-grid .laptop-card");

  filterBtns.forEach(function (btn) {
    btn.addEventListener("click", function () {
      filterBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");

      const filter = btn.getAttribute("data-filter");

      laptopCards.forEach(function (card) {
        const ram = (card.getAttribute("data-ram") || "").toLowerCase();
        const os = (card.getAttribute("data-os") || "").toLowerCase();

        let visible = true;
        if (filter === "high-ram") {
          visible = ram.includes("16") || ram.includes("32") || ram.includes("64");
        } else if (filter === "linux") {
          visible = os.includes("linux") || os.includes("ubuntu");
        } else if (filter === "windows") {
          visible = os.includes("windows");
        }

        if (visible) {
          card.style.display = "flex";
          card.style.opacity = "0";
          card.style.transform = "translateY(10px)";
          setTimeout(function () {
            card.style.transition = "opacity 0.3s ease, transform 0.3s ease";
            card.style.opacity = "1";
            card.style.transform = "translateY(0)";
          }, 30);
        } else {
          card.style.display = "none";
        }
      });
    });
  });

  // 6. Interactive Rewards & Impact Calculator
  const sliderLaptops = document.getElementById("slider-laptops");
  const sliderLoans = document.getElementById("slider-loans");
  const sliderLaptopsVal = document.getElementById("slider-laptops-val");
  const sliderLoansVal = document.getElementById("slider-loans-val");
  const calcTotalCoins = document.getElementById("calc-total-coins");
  const calcTierBadge = document.getElementById("calc-tier-badge");

  function updateCalculator() {
    if (!sliderLaptops || !sliderLoans || !calcTotalCoins) return;

    const laptops = parseInt(sliderLaptops.value, 10);
    const loans = parseInt(sliderLoans.value, 10);

    sliderLaptopsVal.textContent = laptops === 1 ? "1 Laptop" : `${laptops} Laptops`;
    sliderLoansVal.textContent = loans === 1 ? "1 Loan" : `${loans} Loans`;

    // 10 coins per laptop listed, 5 coins per completed loan period
    const totalCoins = laptops * 10 + loans * 5;
    calcTotalCoins.textContent = totalCoins;

    // Reputation Tier Badge
    if (totalCoins < 25) {
      calcTierBadge.textContent = "Bronze Contributor";
      calcTierBadge.style.color = "#d97706";
    } else if (totalCoins < 50) {
      calcTierBadge.textContent = "Silver Scholar";
      calcTierBadge.style.color = "#38bdf8";
    } else if (totalCoins < 80) {
      calcTierBadge.textContent = "Gold Hardware Champion";
      calcTierBadge.style.color = "#fbbf24";
    } else {
      calcTierBadge.textContent = "Diamond Campus Leader ⭐";
      calcTierBadge.style.color = "#c084fc";
    }
  }

  if (sliderLaptops && sliderLoans) {
    sliderLaptops.addEventListener("input", updateCalculator);
    sliderLoans.addEventListener("input", updateCalculator);
    updateCalculator();
  }

  // 7. Interactive FAQ Accordion
  const accordionItems = document.querySelectorAll(".accordion-item");
  accordionItems.forEach(function (item) {
    const header = item.querySelector(".accordion-header");
    if (header) {
      header.addEventListener("click", function () {
        const isActive = item.classList.contains("active");

        // Close other items
        accordionItems.forEach((other) => {
          if (other !== item) {
            other.classList.remove("active");
          }
        });

        // Toggle current item
        if (isActive) {
          item.classList.remove("active");
        } else {
          item.classList.add("active");
        }
      });
    }
  });

  // 8. Mobile Navigation Toggle
  const mobileBtn = document.querySelector(".mobile-menu-btn");
  const navLinks = document.querySelector(".nav-links");
  if (mobileBtn && navLinks) {
    mobileBtn.addEventListener("click", function () {
      navLinks.classList.toggle("active");
    });
  }

  // 9. Auto-dismiss alerts after 6 seconds
  const alerts = document.querySelectorAll(".alert");
  alerts.forEach(function (alert) {
    setTimeout(function () {
      alert.style.transition = "opacity 0.5s ease";
      alert.style.opacity = "0";
      setTimeout(function () {
        alert.remove();
      }, 500);
    }, 6000);
  });

  // 10. Date range inputs validation helper
  const startDateInput = document.querySelector('input[name="start_date"]');
  const endDateInput = document.querySelector('input[name="end_date"]');
  if (startDateInput && endDateInput) {
    const today = new Date().toISOString().split("T")[0];
    if (!startDateInput.getAttribute("min")) {
      startDateInput.setAttribute("min", today);
    }

    startDateInput.addEventListener("change", function () {
      if (startDateInput.value) {
        endDateInput.setAttribute("min", startDateInput.value);
        if (endDateInput.value && endDateInput.value < startDateInput.value) {
          endDateInput.value = startDateInput.value;
        }
      }
    });
  }

  // 11. Modal handlers
  const modalTriggers = document.querySelectorAll("[data-modal-target]");
  modalTriggers.forEach(function (trigger) {
    trigger.addEventListener("click", function () {
      const targetId = trigger.getAttribute("data-modal-target");
      const modal = document.getElementById(targetId);
      if (modal) {
        modal.classList.add("open");
      }
    });
  });

  const modalCloses = document.querySelectorAll("[data-modal-close]");
  modalCloses.forEach(function (closeBtn) {
    closeBtn.addEventListener("click", function () {
      const modal = closeBtn.closest(".modal-backdrop");
      if (modal) {
        modal.classList.remove("open");
      }
    });
  });
});
