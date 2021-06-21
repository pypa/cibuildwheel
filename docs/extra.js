// add classes for code-block-filename styling
$('.rst-content pre')
    .prev('blockquote')
    .addClass('code-block-filename');

var tabConversionIterations = 0

// convert tab admonition to tabs
while (true) {
  const firstTab = $('.rst-content .admonition.tab').first()
  if (firstTab.length == 0) break;

  const otherTabs = firstTab.nextUntil(':not(.admonition.tab)');
  const allTabs = $($.merge($.merge([], firstTab), otherTabs));

  const tabContainer = $('<div>').addClass('tabs');
  const headerContainer = $('<div>').addClass('tabs-header');
  const contentContainer = $('<div>').addClass('tabs-content');

  tabContainer.insertBefore(firstTab);
  tabContainer.append(headerContainer, contentContainer)

  // add extra classes from the first tab to the container
  const classes = Array.from(firstTab[0].classList)

  for (let i = 0; i < classes.length; i++) {
    const element = classes[i];
    if (element == 'tab' || element == 'admonition') {
      continue
    }
    tabContainer.addClass(element)
  }

  const selectTab = function (index) {
    headerContainer.children().removeClass('active')
    headerContainer.children().eq(index).addClass('active')
    contentContainer.children().hide()
    contentContainer.children().eq(index).show()
  }

  allTabs.each(function (tabI, el) {
    const $el = $(el)
    const titleElement = $el.children('.admonition-title')
    const title = titleElement.text()
    const button = $('<button>').text(title)
    button.click(function () {
      selectTab(tabI)
    })
    headerContainer.append(button)

    titleElement.remove()
    $el.removeClass('admonition')
    contentContainer.append($el)
  })

  selectTab(0)

  // this will catch infinite loops which can occur when editing the above
  if (tabConversionIterations++ > 1000) throw 'too many iterations'
}
