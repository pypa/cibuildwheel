---
title: Changelog
---

{%
   includemarkdown "../README.md"
   start="<!--changelog-start-->"
   end="<!--changelog-end-->"
%}

<script>
  // undo the scrollTop that the theme did on this page, as there are loads
  // of toc entries and it's disorientating.
  window.addEventListener('DOMContentLoaded', function() {
    $('.wy-nav-side').scrollTop(0)
  })
</script>
