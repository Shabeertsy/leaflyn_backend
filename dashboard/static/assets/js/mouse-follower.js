document.addEventListener("DOMContentLoaded", () => {
    const follower = document.createElement("div");
    follower.id = "mouse-follower";
    document.body.appendChild(follower);

    const moveFollower = (e) => {
        follower.style.left = `${e.clientX}px`;
        follower.style.top = `${e.clientY}px`;
    };

    document.addEventListener("mousemove", moveFollower);
});
