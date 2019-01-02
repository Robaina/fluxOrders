graphStyle = [
  {
    selector: 'node',
    style: {
        'label': 'data(label)',
        'width': '200%',
        'height': '200%',
        'color': 'black',
        'background-color': '#737373',
        'font-size': 0,
        'text-halign': 'center'
    }
  },

  {
    selector: 'edge',
    style: {
        'width': '5%',
        'line-color': 'grey',
        'target-arrow-color': 'grey',
        'target-arrow-shape': 'triangle',
        'control-point-step-size': '140px',
        'curve-style': 'unbundled-bezier'
    }
  },

  {
    selector: '.childrenEdges',
    style: {
        'width': '35%',
        'line-color': '#5a61c2',
        'target-arrow-color': '#5a61c2',
        'arrow-scale': 3
    }
  },

  {
    selector: '.parentEdges',
    style: {
        'width': '35%',
        'line-color': '#ed5e9c',
        'target-arrow-color': '#ed5e9c',
        'arrow-scale': 3
    }
  },

  {
    selector: '.childrenNodes',
    style: {
      'background-color': '#5a61c2',
      'text-background-color': '#ebebeb',
      'text-background-opacity': 0,
      'font-size': 300,
    }
  },

  {
    selector: '.parentNodes',
    style: {
      'background-color': '#ed5e9c',
      'text-background-color': '#ebebeb',
      'text-background-opacity': 0,
      'font-size': 300,
    }
  },

  {
    selector: '.selectedNode',
    style: {
      'background-color': '#17cfad',
      'z-index': 1,
      'font-size': 350,
    }
  },

  {
    selector: '.selectedSubGraphNode',
    style: {
      'label': 'data(rxnName)',
      'background-color': '#17cfad',
      'text-background-color': '#ebebeb',
      'text-background-opacity': 1,
      'z-index': 1,
      'font-size': 350,
    }
  }

]
