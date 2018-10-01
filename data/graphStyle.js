graphStyle = [
  {
    selector: 'node',
    style: {
        'label': 'data(label)',
        'width': '200px',
        'height': '200px',
        'color': 'black',
        'background-color': 'black',
        'font-size': 0
    }
  },

  {
    selector: 'edge',
    style: {
        'width': '10px',
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
        'width': '50px',
        'line-color': '#5a61c2',
        'target-arrow-color': '#5a61c2',
        'arrow-scale': 3
    }
  },

  {
    selector: '.parentEdges',
    style: {
        'width': '50px',
        'line-color': '#ed5e9c',
        'target-arrow-color': '#ed5e9c',
        'arrow-scale': 3
    }
  },

  {
    selector: '.childrenNodes',
    style: {
      'label': 'data(label)',
      'background-color': '#5a61c2',
      'text-background-color': '#82ded7',
      'text-background-opacity': 0,
      'width': '300px',
      'height': '300px',
      'font-size': 300,
      'text-halign': 'left'
    }
  },

  {
    selector: '.parentNodes',
    style: {
      'label': 'data(label)',
      'background-color': '#ed5e9c',
      'text-background-color': '#82ded7',
      'text-background-opacity': 0,
      'width': '300px',
      'height': '300px',
      'font-size': 300,
      'text-halign': 'left'
    }
  },

  {
    selector: '.selectedNode',
    style: {
      'label': 'data(label)',
      'background-color': '#17cfad',
      'text-background-color': '#82ded7',
      'text-background-opacity': 0,
      'width': '300px',
      'height': '300px',
      'font-size': 300,
      'text-halign': 'left'
    }
  }

]
