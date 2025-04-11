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

/**
 * Redirects the current page based on the path and fragment identifier (hash) in the URL.
 *
 * Example usage:
 * fragmentRedirect([
 *  { source: 'setup/#github-actions', destination: 'ci-services' }
 *  { source: 'faq/#macosx', destination: 'platforms#apple' }
 * ])
 */
function fragmentRedirect(redirects) {
  const href = window.location.href;
  const hash = window.location.hash;

  for (const redirect of redirects) {
    const source = redirect.source;
    const destination = redirect.destination;

    if (endswith(href, source)) {
      // Redirect to the destination path, with the same fragment identifier
      // specified in the destination path, otherwise, keep the same hash
      // from the current URL.
      const destinationIncludesHash = destination.includes('#');
      let newUrl = href.replace(source, destination);
      if (!destinationIncludesHash) {
        newUrl += hash;
      }
      console.log('Redirecting to:', newUrl);
      window.location.replace(newUrl);
      return
    }
  }
}

function endswith(str, suffix) {
  return str.indexOf(suffix, str.length - suffix.length) !== -1;
}

fragmentRedirect([
  { source: 'setup/#github-actions', destination: 'ci-services/' },
  { source: 'setup/#azure-pipelines', destination: 'ci-services/' },
  { source: 'setup/#travis-ci', destination: 'ci-services/' },
  { source: 'setup/#appveyor', destination: 'ci-services/' },
  { source: 'setup/#circleci', destination: 'ci-services/' },
  { source: 'setup/#gitlab-ci', destination: 'ci-services/' },
  { source: 'setup/#cirrus-ci', destination: 'ci-services/' },

  { source: 'faq/#linux-builds-in-containers', destination: 'platforms/#linux-containers' },
  { source: 'faq/#apple-silicon', destination: 'platforms/#macos-architectures' },
  { source: 'faq/#windows-arm64', destination: 'platforms/#windows-arm64' },
]);
