function plotChart(selectedNodeID) {

  let windowHeight = window.innerHeight;
  let windowWidth = window.innerWidth;
  let barChart = document.getElementById("barChart");

  let childrenSubsystems = {};
  childrenNodes.forEach(function(node) {
    let childrenSubsystem = node.data("subsystem");
    if (childrenSubsystem.replace(/\s/g, "")) {
      childrenSubsystems[childrenSubsystem] = childrenSubsystems[childrenSubsystem] + 1 || 1;
    }
  });
  let parentSubsystems = {};
  parentNodes.forEach(function(node) {
    let parentSubsystem = node.data("subsystem");
    if (parentSubsystem.replace(/\s/g, "")) {
      parentSubsystems[parentSubsystem] = parentSubsystems[parentSubsystem] + 1 || 1;
    }
  });

  let barData = [{
      y: Object.values(childrenSubsystems),
      x: Object.keys(childrenSubsystems),
      width: 0.4,
      name: "Children",
      type: "bar",
      marker: {
        color: "#5a61c2"
      }
    },
    {
      y: Object.values(parentSubsystems),
      x: Object.keys(parentSubsystems),
      width: 0.4,
      name: "Parent",
      type: "bar",
      marker: {
        color: "#ed5e9c"
      }
    }
  ];

  let childrenbarTitle, parentbarTitle;
  if (Object.keys(childrenSubsystems).length > 0) {
    childrenbarTitle = "Chidrens";
  } else {
    childrenbarTitle = '';
  }
  if (Object.keys(parentSubsystems).length > 0) {
    parentbarTitle = "Parents";
  } else {
    parentbarTitle = '';
  }
  let fontColor = 'rgb(182, 182, 182)';
  let largeFontSize = 13;
  let smallFontSize = 8;
  let largeHeight = windowHeight / 2.5;
  let smallHeight = windowHeight / 3.5;
  let largeWidth = windowWidth / 2.2;
  let smallWidth = windowWidth / 1.5;

  let barLayout = {
    font:{
      family: "Raleway, sans-serif",
      margin: 0,
      color: fontColor
    },
    useResizeHandler: true,
    autosize: true,
    height: undefined,
    width: undefined,
    paper_bgcolor: "rgba(195, 195, 195, 0)",
    plot_bgcolor: "rgba(78, 78, 78, 0.34)",

    xaxis: {
      ticks: "inside",
      tickangle: 45,
      autotick: false,
      tickwidth: 1,
      automargin: true,
      tickfont: {
        size: undefined,
        color: fontColor
      },
    },
    yaxis: {
      tickfont: {
        size: undefined
      },
      title: 'number of reactions',
      titlefont: {
        size: undefined,
        color: fontColor
      }
    },
    legend: {
      x: 0.8,
      y: 0.92,
      font: {
        size: undefined
      }
    },
    margin: {
      t: 0,
      l: 30,
      r: 80,
      b: 0
  }

  };

  // Workaround to kinda allow responsive font size in plot.ly
  let isMobile = windowWidth < 800;
  let isLandscape = windowWidth > windowHeight;
  let isPortrait = windowWidth < windowHeight;

  if (isMobile) {
    barLayout.xaxis.tickfont.size = smallFontSize;
    barLayout.xaxis.tickangle = 75;
    barLayout.yaxis.tickfont.size = smallFontSize;
    barLayout.yaxis.titlefont.size = smallFontSize;
    barLayout.legend.font.size = smallFontSize;
    barLayout.margin.r = 0;
    barLayout.height = smallHeight;

  } else {
    barLayout.xaxis.tickfont.size = largeFontSize;
    barLayout.yaxis.tickfont.size = largeFontSize;
    barLayout.yaxis.titlefont.size = largeFontSize;
    barLayout.legend.font.size = largeFontSize;
  }

  Plotly.newPlot("barChart", barData, barLayout, {responsive: true});

};
