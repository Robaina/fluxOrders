
let rxnNameLabels = rxnLabels = [];
let option;
let selectedNodeID = "#CS";
let buttonPressed = false;
let oldLabel, oldColor;
let inputRxnName, inputRxnLabel, hoveredNodeID, subcyHoveredNodeID;
let graphContainer = document.getElementById("cy");

// Retrieve array of reaction names and create dropdown list
function fillMissingReactionNames() {
  for (let n=0; n < data['nodes'].length; n++) {
    if (data['nodes'][n]['data']['rxnName'] === " ") {
      data['nodes'][n]['data']['rxnName'] = data['nodes'][n]['data']['label'];
    }
  }
}

function fillMissingSubSystems() {
  for (let n=0; n < data['nodes'].length; n++) {
    if (data['nodes'][n]['data']['subsystem'] === " ") {
      data['nodes'][n]['data']['subsystem'] = "Other";
    }
  }
}

fillMissingReactionNames();
fillMissingSubSystems();

for (node of data['nodes']) {

  inputRxnName = node['data']['rxnName'];
  inputRxnLabel = node['data']['label'];
  rxnNameLabels.push(inputRxnName);
  rxnLabels.push(inputRxnLabel);
  option = document.createElement('option');
  option.text = inputRxnName + " (" + inputRxnLabel + ")";
  option.value = inputRxnLabel;
  option.setAttribute("id", inputRxnLabel);
  if ("#" + inputRxnLabel === selectedNodeID) {
    option.selected = "selected";
  }
  document.getElementById("select-list").add(option);
}

function changeSelectedReaction() {
  let selector = document.getElementById("select-list");
  selectedNodeID = "#" + selector[selector.selectedIndex].value;
  initializeGraph(selectedNodeID);
}

// Define graph object
let cy = cytoscape({
  container: graphContainer,
  elements: data,
  style: graphStyle,
});

// Initialize graph
function initializeGraph(selectedNodeID) {

  selectNodes(cy, selectedNodeID);
  cy.layout(options).run();
  plotChart(selectedNodeID);

  // Modify the position of some nodes a little bit
  xposGLYCDx = cy.$('#GLYCDx').renderedPosition('x');
  yposGLYCDx = cy.$('#GLYCDx').renderedPosition('y');
  xposGLYK = cy.$('#GLYK').renderedPosition('x');
  yposGLYK = cy.$('#GLYK').renderedPosition('y');
  cy.$('#GLYCDx').renderedPosition('x', (1 - 0.5) * xposGLYCDx);
  cy.$('#GLYCDx').renderedPosition('y', (1 + 0.08) * yposGLYCDx);
  cy.$('#GLYK').renderedPosition('x', (1 + 0.45) * xposGLYK);
  cy.$('#GLYK').renderedPosition('y', (1 + 0.08) * yposGLYK);
  xposATPS4rpp = cy.$('#ATPS4rpp').renderedPosition('x');
  cy.$('#ATPS4rpp').renderedPosition('x', xposATPS4rpp - 50);
  xposACONTa = cy.$('#ACONTa').renderedPosition('x');
  cy.$('#ACONTa').renderedPosition('x', xposACONTa + 25);
  xposACONTb = cy.$('#ACONTb').renderedPosition('x');
  cy.$('#ACONTb').renderedPosition('x', xposACONTb + 50);
}

initializeGraph(selectedNodeID);

// Interactive block
cy.on('mouseover', 'node', function(event) {
  hoveredNodeID = '#' + this.id();
  if (hoveredNodeID !== selectedNodeID) {
    cy.$(hoveredNodeID).addClass('selectedNode');
  }
  cy.$(hoveredNodeID).addClass('selectedSubGraphNode');
});
cy.on('mouseout', 'node', function(event) {
  if (hoveredNodeID !== selectedNodeID) {
    cy.$(hoveredNodeID).removeClass('selectedNode');
  }
  cy.$(hoveredNodeID).removeClass('selectedSubGraphNode');
});

cy.on('click tap', 'node', function(event) {
  selectedNodeID = '#' + this.id();
  document.getElementById(this.id()).selected = "selected";
  selectNodes(cy, selectedNodeID);
  plotChart(selectedNodeID);
});

function selectNodes(cy, selectedNodeID) {
  childrenNodes = cy.$(selectedNodeID).successors('node');
  parentNodes = cy.$(selectedNodeID).predecessors('node');
  childrenEdges = cy.$(selectedNodeID).successors('edge');
  parentEdges = cy.$(selectedNodeID).predecessors('edge');

  // Change style classes on click
  cy.batch(function() {
    cy.elements().not(childrenNodes, parentNodes).classes('node');
    childrenNodes.classes('childrenNodes');
    childrenEdges.classes('childrenEdges');
    parentNodes.classes('parentNodes');
    parentEdges.classes('parentEdges');
    cy.$(selectedNodeID).classes('selectedNode');
  });

  cy.fit();

};
