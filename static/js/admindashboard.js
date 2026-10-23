document.getElementById("autodate").innerText = new Date().toLocaleDateString();

function filterTeachers(select, programId) {
    if (!select) return;
    for (const option of select.options) {
        if (!option.value) {
            option.hidden = false;
            continue;
        }
        option.hidden = !programId || option.dataset.programId !== programId;
    }
    if (select.selectedOptions[0]?.hidden) select.value = "";
}

const subjectProgram = document.getElementById("subject-program");
const subjectTeacher = document.getElementById("subject-teacher");

if (subjectProgram && subjectTeacher) {
    const updateTeacherChoices = () => filterTeachers(subjectTeacher, subjectProgram.value);
    subjectProgram.addEventListener("change", updateTeacherChoices);
    updateTeacherChoices();
}

document.querySelectorAll(".subject-teacher-form").forEach(form => {
    filterTeachers(form.querySelector('select[name="teacher_id"]'), form.dataset.programId);
});

const dashboard = document.querySelector(".dashboard-container");
const sidebarToggle = document.getElementById("sidebarToggle");
const closeNav = document.getElementById("closenav");

if (dashboard && sidebarToggle && closeNav) {
    sidebarToggle.addEventListener("click", function () {
        dashboard.classList.add("sidebar-open");
    });

    closeNav.addEventListener("click", function () {
        dashboard.classList.remove("sidebar-open");
    });
}
