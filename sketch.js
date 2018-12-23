// Define graph object
let cy = cytoscape({
  container: document.getElementById('cy'),
  elements: data,
  style: graphStyle,
});

let subcy = cytoscape({
  container: document.getElementById('subcy'),
  style: graphStyle,
});

// Initialize graph
let nodeID = '#PFL';
let selectedNode = null;
let oldLabel, oldColor;
selectNodes(cy, nodeID);
cy.layout(options).run();
plotSubGraph(cy, subcy, nodeID)
plotPieChart(nodeID);

// Modify the position of some nodes a little bit
xposGLYCDx = cy.$('#GLYCDx').renderedPosition('x');
yposGLYCDx = cy.$('#GLYCDx').renderedPosition('y');
yposGLYK = cy.$('#GLYK').renderedPosition('y');
cy.$('#GLYCDx').renderedPosition('x', xposGLYCDx - 150);
cy.$('#GLYCDx').renderedPosition('y', yposGLYCDx + 50);
cy.$('#GLYK').renderedPosition('y', yposGLYK + 50);
xposATPS4rpp = cy.$('#ATPS4rpp').renderedPosition('x');
cy.$('#ATPS4rpp').renderedPosition('x', xposATPS4rpp - 50);
xposACONTa = cy.$('#ACONTa').renderedPosition('x');
cy.$('#ACONTa').renderedPosition('x', xposACONTa + 25);
xposACONTb = cy.$('#ACONTb').renderedPosition('x');
cy.$('#ACONTb').renderedPosition('x', xposACONTb + 50);

// Highlight nodes when hovering
cy.on('mouseover', 'node', function(event) {
  selectedNode = cy.$('#' + this.id());
  oldColor = selectedNode.css('background-color');
  selectedNode.css('background-color', '#17cfad');
});
cy.on('mouseout', 'node', function(event) {
  selectedNode.css('background-color', oldColor);
});

subcy.on('mouseover', 'node', function(event) {
  selectedNode = subcy.$('#' + this.id());
  oldLabel = selectedNode.css('label');
  oldColor = selectedNode.css('background-color');
  let rxnName = selectedNode.data('rxnName');
  selectedNode.css('label', rxnName);
  selectedNode.css('text-background-opacity', 1);
  selectedNode.css('background-color', '#17cfad');
});
subcy.on('mouseout', 'node', function(event) {
  selectedNode.css('label', oldLabel);
  selectedNode.css('text-background-opacity', 0);
  selectedNode.css('background-color', oldColor);
});

// Interactive block
cy.on('click tap', 'node', function(event) {

  let nodeID = '#' + this.id();
  selectNodes(cy, nodeID);
  plotSubGraph(cy, subcy, nodeID)
  plotPieChart(nodeID);

  document.getElementById('rxnName').innerHTML = cy.$(nodeID).data('rxnName');
  // + ' ' + childrenNodes.length
  // + ' ' + parentNodes.length;
});

// Helper functions
function selectNodes(cy, nodeID) {

  childrenNodes = cy.$(nodeID).successors('node');
  parentNodes = cy.$(nodeID).predecessors('node');
  childrenEdges = cy.$(nodeID).successors('edge');
  parentEdges = cy.$(nodeID).predecessors('edge');

  // Change style classes on click
  cy.batch(function() {
    cy.elements().not(childrenNodes, parentNodes).classes('node');
    childrenNodes.classes('childrenNodes');
    childrenEdges.classes('childrenEdges');
    parentNodes.classes('parentNodes');
    parentEdges.classes('parentEdges');
    cy.$(nodeID).classes('selectedNode');
  });

};

function plotSubGraph(cy, subcy, nodeID) {
  subcy.elements().remove();
  for (element of [cy.$(nodeID), childrenNodes, parentNodes, childrenEdges, parentEdges]) {
    subcy.add(element.jsons());
  }
  subcy.layout(options).run();
};

function plotPieChart(nodeID) {

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
      text: 'CO2',
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
    childrenPieTitle = 'Chidren';
  } else {
    childrenPieTitle = '';
  }
  if (Object.keys(parentSubsystems).length > 0) {
    parentPieTitle = 'Parent';
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
        text: childrenPieTitle,
        x: 0.15,
        y: 0.5
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
        text: parentPieTitle,
        x: 0.83,
        y: 0.5
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
  document.getElementById('rxnName').innerHTML = cy.$(nodeID).data('rxnName');

};
