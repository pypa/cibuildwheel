// add classes for code-block-filename styling
$('.rst-content pre')
    .prev('blockquote')
    .addClass('code-block-filename');

var i=0

// convert tab admonition to tabs
while (true) {
  const firstTab = $('.rst-content .admonition.tab').first()
  if (firstTab.length == 0) break;

  const otherTabs = firstTab.nextUntil(':not(.admonition.tab)');
  const allTabs = $($.merge($.merge([], firstTab), otherTabs));

  const tabContainer = $('<div>').addClass('tabs');
  const headerContainer = $('<div>').addClass('tabs-header');
  const contentContainer = $('<div>').addClass('tabs-content');
  console.log(allTabs)

  tabContainer.insertBefore(firstTab);
  tabContainer.append(headerContainer, contentContainer)

  const selectTab = function (index) {
    headerContainer.children().removeClass('active')
    headerContainer.children().eq(index).addClass('active')
    contentContainer.children().hide()
    contentContainer.children().eq(index).show()
  }

  allTabs.each(function (i, el) {
    const $el = $(el)
    const titleElement = $el.children('.admonition-title')
    const title = titleElement.text()
    const button = $('<button>').text(title)
    button.click(function () {
      selectTab(i)
    })
    headerContainer.append(button)

    titleElement.remove()
    $el.removeClass('admonition')
    contentContainer.append($el)
  })

  selectTab(0)

  if (i++ > 1000) throw 'too many iterations'
}
