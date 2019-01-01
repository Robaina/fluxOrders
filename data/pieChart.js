function plotPieChart(selectedNodeID) {

  let childrenSubsystems = {};
  childrenNodes.forEach(function(node) {
    let childrenSubsystem = node.data('subsystem');
    if (childrenSubsystem.replace(/\s/g, "")) {
      childrenSubsystems[childrenSubsystem] = childrenSubsystems[childrenSubsystem] + 1 || 1;
    }
  });
  let parentSubsystems = {};
  parentNodes.forEach(function(node) {
    let parentSubsystem = node.data('subsystem');
    if (parentSubsystem.replace(/\s/g, "")) {
      parentSubsystems[parentSubsystem] = parentSubsystems[parentSubsystem] + 1 || 1;
    }
  });

  let pieData = [{
      values: Object.values(childrenSubsystems),
      labels: Object.keys(childrenSubsystems),
      domain: {
        x: [0, .48]
      },
      name: 'Children',
      hole: .4,
      type: 'pie'
    },
    {
      values: Object.values(parentSubsystems),
      labels: Object.keys(parentSubsystems),
      textposition: 'inside',
      domain: {
        x: [.52, 1]
      },
      name: 'Parent',
      hole: .4,
      type: 'pie'
    }
  ];

  let childrenPieTitle, parentPieTitle;
  if (Object.keys(childrenSubsystems).length > 0) {
    childrenPieTitle = 'Chidrens';
  } else {
    childrenPieTitle = '';
  }
  if (Object.keys(parentSubsystems).length > 0) {
    parentPieTitle = 'Parents';
  } else {
    parentPieTitle = '';
  }

  let pieLayout = {
    annotations: [{
        font: {
          size: 20
        },
        margin: {
          l: 0,
          r: 0,
          b: 0,
          t: 0,
          pad: 0
        },
        showarrow: false,
        text: childrenPieTitle + " (" + childrenNodes.length.toString() + ")",
        x: 0.17,
        y: 0.9
      },
      {
        font: {
          size: 20
        },
        margin: {
          l: 0,
          r: 0,
          b: 0,
          t: 0,
          pad: 0
        },
        showarrow: false,
        text: parentPieTitle + " (" + parentNodes.length.toString() + ")",
        x: 0.87,
        y: 0.9
      }
    ],
    height: window.innerWidth / 3,
    width: window.innerWidth / 2.5,
    margin: {
      l: 0,
      r: 0,
      b: 0,
      t: 0,
      pad: 0
    },
    showlegend: false,
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    xaxis: {
      range: [0, 1]
    },
    yaxis: {
      range: [0, 1]
    }

  };

  Plotly.newPlot('pieChart', pieData, pieLayout);
  document.getElementById('reaction').innerHTML = cy.$(selectedNodeID).data('rxnName');

};
