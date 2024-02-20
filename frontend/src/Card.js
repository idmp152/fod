import React from 'react';
import './Card.css';

function Card(props) {
  const handleImageLoad = event => {
    if (event.target.naturalWidth/event.target.naturalHeight <=  1/1.1) {
      event.target.parentElement.classList.add("large")
    } else if (event.target.naturalWidth/event.target.naturalHeight <= 1/1.6) {
      event.target.parentElement.classList.add("medium")
    } else {
      event.target.parentElement.classList.add("small")
    }
  }

  return (
      <div className="card small">
        <img
          className="pinImage"
          style={{height: 'fit-content'}}
          src={props.url}
          alt=""
          onLoad={handleImageLoad}
        />
      </div>
  )
}

export default Card;
