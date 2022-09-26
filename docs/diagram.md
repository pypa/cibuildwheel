<div id="flow-diagram">
  <div class="diagram-grid" v-bind:style="gridStyle">
    <!-- BEHIND THE GRID CONTENT -->
    <!-- line for each platform -->
    <div class="grid-line" style="grid-row-start: 3"></div>
    <div class="grid-line" style="grid-row-start: 4"></div>
    <div class="grid-line" style="grid-row-start: 5"></div>
    <!-- the docker container outline -->
    <div class="grid-outline docker">
      <div class="outline">
        Manylinux container
      </div>
    </div>
    <!-- the venv outlines -->
    <div class="grid-outline testVenv" style="grid-row-start: 3">
      <div class="outline">Test virtualenv</div>
    </div>
    <div class="grid-outline testVenv" style="grid-row-start: 4"><div class="outline"></div></div>
    <div class="grid-outline testVenv" style="grid-row-start: 5"><div class="outline"></div></div>
    <!-- THE GRID CONTENT -->
    <!-- the row labels -->
    <div class="grid-row-label" style="grid-row-start: 3">Linux</div>
    <div class="grid-row-label" style="grid-row-start: 4">macOS</div>
    <div class="grid-row-label" style="grid-row-start: 5">Windows</div>
    <!-- the column labels -->
    <div class="grid-column-label"
         style="grid-row: 1 / span 1; grid-column: 5 / -3">
      <div class="label">For each version of Python</div>
    </div>
    <div class="grid-column-label"
         style="grid-row: 2 / span 1;
                grid-column: 9 / -3;
                margin-bottom: 0.5em;">
      <div class="label">If tests are configured</div>
    </div>
    <!-- the steps -->
    <div class="step" v-for="(step, sIndex) in diagram.steps">
      <component v-for="action in step"
                 class="action"
                 v-bind:is="action.href ? 'a' : 'div'"
                 v-bind:href="action.href">
        <div class="dots" v-if="action.style == 'dot'">
          <div class="dot"
               v-info="action"
               v-for="(platform, pIndex) in platforms"
               v-if="action.platforms.includes(platform)"
               v-bind:style="{gridRowStart: `${pIndex+3}`,
                              gridColumnStart: `${sIndex+2}`}">
            <div class="dot-graphic"></div>
          </div>
        </div>
        <div class="block-container" v-if="action.style == 'block'">
          <div class="block"
               v-info="action"
               v-bind:style="{...blockStyle(action),
                              gridColumnStart: `${sIndex+2}`}">
            {{action.label}}
          </div>
        </div>
      </a>
    </div>
  </div>
</div>

<noscript>
  <img src="data/how-it-works.png" alt="Diagram showing the steps for each platform">
  <p><strong>Enable JavaScript for an interactive version of this diagram.</strong></p>
</noscript>

<script type="module" async>
  import Vue from 'https://cdn.jsdelivr.net/npm/vue@2.6.14/dist/vue.esm.browser.js'
  import 'https://unpkg.com/@popperjs/core@2/dist/umd/popper.min.js'
  import 'https://unpkg.com/tippy.js@6/dist/tippy-bundle.umd.js'

  const diagram = {
    steps: [
      [
        {
          label: 'copy project into container',
          platforms: ['linux'],
          style: 'block',
          width: 2,
        },
      ],
      [], // empty column so that the manylinux outline intersects the previous column in the middle.
      [
        {
          href: 'options/#before-all',
          platforms: ['linux', 'macos', 'windows'],
          style: 'dot',
          tooltip: {
            title: 'CIBW_BEFORE_ALL',
            tag: 'Optional step',
            description: 'Execute a shell command on the build system before any wheels are built.'
          },
        },
      ],
      [
        {
          label: 'Install Python',
          platforms: ['macos', 'windows'],
          style: 'block',
          tooltip: {
            description: 'Install the version of Python required to build this wheel.'
          },
        },
      ],
      [
        {
          href: 'options/#before-build',
          platforms: ['linux', 'macos', 'windows'],
          style: 'dot',
          tooltip: {
            title: 'CIBW_BEFORE_BUILD',
            tag: 'Optional step',
            description: "Execute a shell command preparing each wheel's build.",
          },
        },
      ],
      [
        {
          label: 'Build wheel',
          href: 'options/#build-frontend',
          platforms: ['linux', 'macos', 'windows'],
          style: 'block',
          tooltip: {
            title: 'CIBW_BUILD_FRONTEND',
            tag: 'Customisable step',
            description: 'Build the wheel according to your package configuration, using the frontend of your choice - pip or build.'
          },
        },
      ],
      [
        {
          label: 'Repair using auditwheel',
          href: 'options/#repair-wheel-command',
          platforms: ['linux'],
          style: 'block',
          tooltip: {
            title: 'CIBW_REPAIR_WHEEL_COMMAND',
            tag: 'Customisable step',
            description: 'Bundle shared libraries and ensure manylinux compliance by running auditwheel on each built wheel.'
          },
        },
        {
          label: 'Repair using delocate',
          href: 'options/#repair-wheel-command',
          platforms: ['macos'],
          style: 'block',
          tooltip: {
            title: 'CIBW_REPAIR_WHEEL_COMMAND',
            tag: 'Customisable step',
            description: 'Bundle shared libraries by running delocate on each built wheel.'
          },
        },
        {
          env: "CIBW_REPAIR_WHEEL_COMMAND",
          href: 'options/#repair-wheel-command',
          label: 'repair wheel',
          platforms: ['windows'],
          style: 'dot',
          optional: true,
          tooltip: {
            title: 'CIBW_REPAIR_WHEEL_COMMAND',
            tag: 'Optional step',
            description: 'Execute a shell command to repair each built wheel'
          },
        },
      ],
      [
        {
          href: 'options/#before-test',
          platforms: ['linux', 'macos', 'windows'],
          style: 'dot',
          tooltip: {
            title: 'CIBW_BEFORE_TEST',
            tag: 'Optional step',
            description: 'Execute a shell command before testing each wheel'
          },
        },
      ],
      [
        {
          label: 'Install wheel',
          platforms: ['linux', 'macos', 'windows'],
          style: 'block',
          tooltip: {
            description: 'Install the wheel we just built into the test virtualenv.'
          },
        },
      ],
      [
        {
          label: 'Test wheel',
          href: 'options/#test-command',
          platforms: ['linux', 'macos', 'windows'],
          style: 'block',
          tooltip: {
            title: 'CIBW_TEST_COMMAND',
            tag: 'Optional step',
            description: 'Execute a shell command to test each built wheel'
          },
        },
      ],
      [
        {
          label: 'Copy wheels out of container',
          platforms: ['linux'],
          style: 'block',
          width: 2,
        },
      ],
      [],
    ]
  }

  const diagramComponent = new Vue({
    el: '#flow-diagram',
    data() {
      return {
        diagram,
        platforms: ['linux', 'macos', 'windows'],
      }
    },
    methods: {
      blockStyle(action) {
        let start, end
        if (action.platforms.includes('linux')) {
          start = 3
        } else if (action.platforms.includes('macos')) {
          start = 4
        } else if (action.platforms.includes('windows')) {
          start = 5
        }

        if (action.platforms.includes('windows')) {
          end = 6
        } else if (action.platforms.includes('macos')) {
          end = 5
        } else if (action.platforms.includes('linux')) {
          end = 4
        }

        return {
          gridRowStart: start.toString(),
          gridRowEnd: end.toString(),
          gridColumnEnd: `span ${action.width || 1}`,
        }
      }
    },
    computed: {
      gridStyle() {
        return {
          gridTemplateRows: `auto auto repeat(${this.platforms.length}, 1fr)`,
          gridTemplateColumns: `repeat(${this.diagram.steps.length+1}, auto)`,
        }
      },
    },
    directives: {
      info: {
        inserted(el, binding) {
          const action = binding.value
          const {env, label, optional=false, description='', href=''} = action
          const tooltip = action.tooltip

          if (tooltip) {
            const tippyInstance = tippy(el, {
              content: `
                <a class="tooltip-contents" href="${href || ''}">
                  <div class="tooltip-title">
                    ${tooltip.title || ''}
                  </div>
                  <div class="tooltip-tag">
                    ${tooltip.tag || ''}
                  </div>
                  <div class="tooltip-description">
                    ${tooltip.description}
                  </div>
                </a>
              `,
              placement: 'right-start',
              allowHTML: true,
              maxWidth: 'none',
              appendTo: document.getElementById('flow-diagram'),
              offset: [0, 10],
              onShow(instance) {
                const stepEl = el.closest('.action')
                stepEl.classList.add('tooltip-open')
                instance.setProps({
                  interactive: tippy.currentInput.isTouch
                })
              },
              onHide() {
                const stepEl = el.closest('.action')
                stepEl.classList.remove('tooltip-open')
              }
            })

            el.addEventListener('click', e => {
              // click event should just open the tooltip on touch devices
              if (tippy.currentInput.isTouch) {
                e.preventDefault()
              }
            })
          }
        }
      }
    }
  })
</script>

<style>
  #flow-diagram {
    background: #fcfcfc;
    /* font-family: Inter; */
    /* font-size: 10px; */
    font-size: 0.7em;
    padding-bottom: 2em;
  }
  .no-js #flow-diagram {
    display: none
  }
  .diagram-grid {
    display: grid;
    overflow-x: auto;
  }
  .platform, .step, .dots, .block-container, .action {
    display: contents;
  }
  .block, .dot {
    position: relative;
    margin: 2em 0.5em;
  }
  .block {
    background-color: #eee;
    /* margin: 0.5em auto; */
    padding: 0.5em;
    max-width: 6em;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
  }
  .dot {
    /* margin: 0.5em; */
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .dot-graphic {
    width: 1.3em;
    height: 1.3em;
    border-radius: 50%;
    background: #DADADA;
  }
  a.action {
    color: inherit;
  }
  .action.tooltip-open .dot-graphic {
    background-color: #416EDA;
  }
  .action.tooltip-open .block {
    background-color: #416EDA;
    color: white;
  }
  .grid-column-label {
    height: 2em;
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 0.5em;
  }
  .grid-column-label::before {
    content: "";
    height: 1px;
    background-color: currentColor;
    position: absolute;
    top: calc(50% - 0.5px);
    left: 0;
    right: 0;
  }
  .grid-column-label .label {
    background: #fcfcfc;
    padding: 0 1em;
    position: relative;
  }
  .grid-row-label {
    grid-column: 1 / span 1;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    text-align: right;
    background: #fcfcfc;
    position: relative;
    padding-right: 1em;
    font-size: 1.1em;
  }
  .grid-line {
    grid-column: 1 / -1;
    grid-row-end: span 1;
    position: relative;
  }
  .grid-line::after {
    content: "";
    height: 1px;
    background-color: #979797;
    position: absolute;
    top: calc(50% - 1px);
    left: 0;
    right: 0;
  }
  .grid-outline {
    grid-row-end: span 1;
    position: relative;
    color: #8f8f8f;
  }
  .grid-outline.docker {
    grid-row: 3 / span 1;
    grid-column: 3 / -2;
  }
  .grid-outline.testVenv {
    grid-column: 9 / span 3;
  }
  .grid-outline .outline {
    position: absolute;
    border: 1px solid #e5e5e5;
    padding: 1px 3px;
  }
  .grid-outline.docker .outline  {
    left: 0;
    right: 0;
    top: 0;
    bottom: 0;
  }
  .grid-outline.testVenv .outline  {
    left: 0;
    right: 0;
    top: 0.5em;
    bottom: 0.5em;
  }

  /* style the tooltip */
  .tippy-box {
    background: white;
    box-shadow: 0 2px 6px -1px rgba(0,0,0,0.12);
    border-radius: 0;
    text-align: left;
    font-size: 1em;
    color: #1F1F1F;
    border: 1px solid rgba(0, 0, 0, 0.02);
    width: 14em;
    min-width: min-content;
  }
  .tippy-box[data-placement^='top'] > .tippy-arrow::before {
    border-top-color: white;
  }
  .tippy-box[data-placement^='bottom'] > .tippy-arrow::before {
    border-bottom-color: white;
  }
  .tippy-box[data-placement^='left'] > .tippy-arrow::before {
    border-left-color: white;
  }
  .tippy-box[data-placement^='right'] > .tippy-arrow::before {
    border-right-color: white;
  }
  a.tooltip-contents {
    color: inherit;
    text-decoration: none;
    display: block;
  }
  .tooltip-title {
    font-weight: 600;
    font-size: 1.1em;
    color: #416EDA;
  }
  .tooltip-tag {
    font-weight: 500;
    text-transform: uppercase;
    font-size: 0.9em;
    color: #C9C9C9;
  }
  .tooltip-description {
    margin-top: 1px;
    margin-bottom: 2px;
  }
</style>
