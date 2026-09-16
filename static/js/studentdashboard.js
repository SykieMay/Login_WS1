const dashboard = document.querySelector(".dashboard-container");
const sidebarToggle = document.getElementById("sidebarToggle");
const closeNav = document.getElementById("closenav");
const profileBtn = document.querySelector(".profile-btn");
const profileMenu = document.querySelector(".profile-menu");

sidebarToggle.addEventListener("click", function() {
    dashboard.classList.add("sidebar-open");
});

closeNav.addEventListener("click", function() {
    dashboard.classList.remove("sidebar-open");
});

profileBtn.addEventListener("click", function() {
    profileMenu.classList.toggle("show");
});

document.addEventListener("click", function(event) {
    if (!event.target.closest(".profile")) {
        profileMenu.classList.remove("show");
    }
});

document.getElementById("autodate").innerText = new Date().toLocaleDateString();