document.addEventListener("DOMContentLoaded", function () {
    // Display today's date
    const dateElement = document.getElementById("autodate");

    if (dateElement) {
        const today = new Date();

        dateElement.textContent = today.toLocaleDateString("en-PH", {
            year: "numeric",
            month: "long",
            day: "numeric"
        });

        dateElement.dateTime = [
            today.getFullYear(),
            String(today.getMonth() + 1).padStart(2, "0"),
            String(today.getDate()).padStart(2, "0")
        ].join("-");
    }

    // Toggle mobile sidebar
    const toggleButton = document.getElementById("sidebarToggle");

    if (toggleButton) {
        toggleButton.setAttribute("aria-expanded", "false");

        toggleButton.addEventListener("click", function () {
            const isOpen = document.body.classList.toggle("sidebar-open");

            toggleButton.setAttribute("aria-expanded", String(isOpen));

            const icon = toggleButton.querySelector("i");

            if (icon) {
                icon.classList.toggle("fa-bars", !isOpen);
                icon.classList.toggle("fa-times", isOpen);
            }
        });
    }

    // Handle sidebar navigation
    document.querySelectorAll("#sidebar-container .navbar a").forEach(function (link) {
        link.addEventListener("click", function () {
            document.body.classList.remove("sidebar-open");

            if (toggleButton) {
                toggleButton.setAttribute("aria-expanded", "false");

                const icon = toggleButton.querySelector("i");

                if (icon) {
                    icon.classList.add("fa-bars");
                    icon.classList.remove("fa-times");
                }
            }

            document.querySelectorAll("#sidebar-container .navbar li").forEach(function (item) {
                item.classList.remove("active");
            });

            const parentItem = link.closest("li");
            const href = link.getAttribute("href");

            if (parentItem && href && href.startsWith("#")) {
                parentItem.classList.add("active");
            }
        });
    });
});

// Open and close assignment and lesson plan forms
function toggleForm(formId) {
    const form = document.getElementById(formId);

    if (!form) {
        console.error("Form not found:", formId);
        return;
    }

    form.hidden = !form.hidden;

    if (!form.hidden) {
        const firstInput = form.querySelector("input, textarea");

        if (firstInput) {
            firstInput.focus();
        }
    }
}