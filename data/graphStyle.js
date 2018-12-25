graphStyle = [
  {
    selector: 'node',
    style: {
        'label': 'data(label)',
        'width': '100%',
        'height': '100%',
        'color': 'black',
        'background-color': 'black',
        'font-size': 0
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
        'width': '20%',
        'line-color': '#5a61c2',
        'target-arrow-color': '#5a61c2',
        'arrow-scale': 3
    }
  },

  {
    selector: '.parentEdges',
    style: {
        'width': '20%',
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
      'text-background-color': '#ebebeb',
      'text-background-opacity': 0,
      'width': '100%',
      'height': '100%',
      'font-size': 150,
      'text-halign': 'center'
    }
  },

  {
    selector: '.parentNodes',
    style: {
      'label': 'data(label)',
      'background-color': '#ed5e9c',
      'text-background-color': '#ebebeb',
      'text-background-opacity': 0,
      'width': '100%',
      'height': '100%',
      'font-size': 150,
      'text-halign': 'center'
    }
  },

  {
    selector: '.selectedNode',
    style: {
      'label': 'data(label)',
      'background-color': '#17cfad',
      'text-background-color': '#ebebeb',
      'text-background-opacity': 0,
      'z-index': 1,
      'width': '100%',
      'height': '100%',
      'font-size': 150,
      'text-halign': 'center'
    }
  }

  // {
  //   oldLabel = selectedNode.css('label');
  //   oldColor = selectedNode.css('background-color');
  //   let rxnName = selectedNode.data('rxnName');
  //   selectedNode.css('label', rxnName);
  //   selectedNode.css('text-background-opacity', 1);
  //   selectedNode.css('background-color', '#17cfad');
  //   selectedNode.css('text-halign', 'centre');
  // }

]
