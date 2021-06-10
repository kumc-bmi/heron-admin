// script to fetch button for top scroll
var scrollbutton = document.getElementById("scrollBtn"); // declare variable for button
window.onscroll = function() {scrollFunction()};

// scroll to the top button becomes visible When the user scrolls down 20px
function scrollFunction() {
  if (document.body.scrollTop > 20 || document.documentElement.scrollTop > 20) {
    scrollbutton.style.display = "block";
  } else {
    scrollbutton.style.display = "none";
  }
}

// click the scroll to top button to move back to the top of the button
function topFunction() {
  document.body.scrollTop = 0;
  document.documentElement.scrollTop = 0;
}