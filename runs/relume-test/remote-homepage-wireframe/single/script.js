const menuToggle = document.querySelector(".menu-toggle");
const menu = document.querySelector("#primary-menu");

if (menuToggle && menu) {
  menuToggle.addEventListener("click", () => {
    const isOpen = menuToggle.getAttribute("aria-expanded") === "true";
    menuToggle.setAttribute("aria-expanded", String(!isOpen));
    menu.classList.toggle("is-open", !isOpen);
  });

  menu.addEventListener("click", (event) => {
    if (event.target.closest("a") && window.matchMedia("(max-width: 767px)").matches) {
      menuToggle.setAttribute("aria-expanded", "false");
      menu.classList.remove("is-open");
    }
  });

  window.addEventListener("resize", () => {
    if (window.matchMedia("(min-width: 768px)").matches) {
      menuToggle.setAttribute("aria-expanded", "false");
      menu.classList.remove("is-open");
    }
  });
}

const testimonialRail = document.querySelector(".testimonial-rail");
const railButtons = document.querySelectorAll("[data-rail-direction]");

railButtons.forEach((button) => {
  button.addEventListener("click", () => {
    if (!testimonialRail) return;

    const direction = Number(button.dataset.railDirection);
    const card = testimonialRail.querySelector(".testimonial-card");
    const distance = card ? card.getBoundingClientRect().width + 16 : 320;

    testimonialRail.scrollBy({
      left: distance * direction,
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
    });
  });
});
